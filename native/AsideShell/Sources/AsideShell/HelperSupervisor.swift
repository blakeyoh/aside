import AppKit
import Foundation
import SwiftUI

typealias HelperProcessFactory = @MainActor (HelperLaunch, [String: String]) -> HelperProcessDriving
typealias HelperScheduler = (TimeInterval, @escaping @MainActor () -> Void) -> Void

enum HelperCaptureState: String, Equatable {
    case idle
    case recording
    case transcribing
}

@MainActor
final class HelperSupervisor: ObservableObject {
    @Published var state: HelperState = .stopped
    @Published var errorMessage: String?
    @Published var permissions: [String: String] = [:]
    @Published var config = HelperConfig()
    @Published var dictionary = HelperDictionary()
    @Published var captureTarget: String?
    @Published var eventLog: [String] = []
    @Published var isRunning = false
    @Published private(set) var processPhase: HelperProcessPhase = .stopped
    @Published private(set) var modelReady = false
    @Published private(set) var permissionsReady = false
    @Published private(set) var captureState: HelperCaptureState = .idle

    private var process: HelperProcessDriving?
    private var lifecycle = HelperLifecycle()
    private var stdoutFrames = LineFrameDecoder()
    private var stderrFrames = LineFrameDecoder()
    private var didScheduleProtocolSmokeExit = false
    private var shutdownCompletions: [() -> Void] = []

    private let processFactory: HelperProcessFactory
    private let scheduler: HelperScheduler
    private let launchResolver: ([String: String]) -> HelperLaunch
    private let environmentProvider: () -> [String: String]
    private let executableCheck: (String) -> Bool
    private let protocolSmokeMode: () -> Bool

    init(
        processFactory: @escaping HelperProcessFactory = { launch, environment in
            FoundationHelperProcess(launch: launch, environment: environment)
        },
        scheduler: @escaping HelperScheduler = { delay, action in
            DispatchQueue.main.asyncAfter(deadline: .now() + delay) {
                Task { @MainActor in
                    action()
                }
            }
        },
        launchResolver: @escaping ([String: String]) -> HelperLaunch = resolvedHelperLaunch,
        environmentProvider: @escaping () -> [String: String] = {
            ProcessInfo.processInfo.environment
        },
        executableCheck: @escaping (String) -> Bool = {
            FileManager.default.isExecutableFile(atPath: $0)
        },
        protocolSmokeMode: @escaping () -> Bool = swiftProtocolSmokeMode
    ) {
        self.processFactory = processFactory
        self.scheduler = scheduler
        self.launchResolver = launchResolver
        self.environmentProvider = environmentProvider
        self.executableCheck = executableCheck
        self.protocolSmokeMode = protocolSmokeMode
    }

    private var isProtocolSmokeMode: Bool {
        protocolSmokeMode()
    }

    var helperDescription: String {
        let launch = launchResolver(environmentProvider())
        return ([launch.executable.path] + launch.arguments).joined(separator: " ")
    }

    func startHelper() {
        guard process == nil else {
            return
        }

        let environment = environmentProvider()
        let launch = launchResolver(environment)
        let executablePath = launch.executable.path
        let generation = lifecycle.beginStart()
        syncProcessPhase()
        resetTransientState()

        guard executableCheck(executablePath) else {
            _ = lifecycle.didFailToLaunch(generation: generation)
            syncProcessPhase()
            state = .error
            errorMessage = "Helper is not executable at \(executablePath). Set ASIDE_PYTHON or run from the repo root after setup.sh."
            appendLog("launch failed: \(executablePath)")
            return
        }

        var childEnvironment = environment
        childEnvironment["PYTHONUNBUFFERED"] = "1"
        if isProtocolSmokeMode {
            childEnvironment["ASIDE_HELPER_PROTOCOL_SMOKE"] = "1"
        }
        if let pythonPath = launch.pythonPath {
            if let existing = childEnvironment["PYTHONPATH"], !existing.isEmpty {
                childEnvironment["PYTHONPATH"] = "\(pythonPath):\(existing)"
            } else {
                childEnvironment["PYTHONPATH"] = pythonPath
            }
        }
        let process = processFactory(launch, childEnvironment)
        self.process = process
        process.stdoutHandler = { [weak self] data in
            Task { @MainActor [weak self] in
                self?.consumeStdout(data, generation: generation)
            }
        }
        process.stderrHandler = { [weak self] data in
            Task { @MainActor [weak self] in
                self?.consumeStderr(data, generation: generation)
            }
        }
        process.exitHandler = { [weak self] status in
            Task { @MainActor [weak self] in
                self?.handleTermination(status: status, generation: generation)
            }
        }

        do {
            try process.run()
            guard lifecycle.didLaunch(generation: generation) else {
                process.forceTermination()
                return
            }
            syncProcessPhase()
            state = .loading
            errorMessage = nil
            isRunning = true
            appendLog("launched helper pid \(process.processIdentifier)")
            scheduler(3.0) { [weak self] in
                self?.handleHandshakeTimeout(generation: generation)
            }
        } catch {
            process.invalidateHandlers()
            self.process = nil
            _ = lifecycle.didFailToLaunch(generation: generation)
            syncProcessPhase()
            state = .error
            errorMessage = "Could not launch helper: \(error.localizedDescription)"
            appendLog("launch error: \(error.localizedDescription)")
            finishShutdownCompletions()
        }
    }

    func restartHelper() {
        guard process != nil else {
            startHelper()
            return
        }
        beginStop(restart: true)
    }

    func shutdownHelper(completion: (() -> Void)? = nil) {
        if let completion {
            shutdownCompletions.append(completion)
        }
        guard process != nil else {
            if state != .error {
                state = .stopped
            }
            finishShutdownCompletions()
            return
        }
        beginStop(restart: false)
    }

    func refreshPermissions() {
        guard lifecycle.handshakeComplete else {
            appendLog("permission refresh deferred until helper handshake")
            return
        }
        send(command: "getPermissions")
    }

    private func beginStop(restart: Bool) {
        guard lifecycle.requestStop(restart: restart) else {
            return
        }
        syncProcessPhase()
        appendLog("shutdown requested")
        send(command: "shutdown")
        process?.closeInput()
        let generation = lifecycle.generation
        scheduler(2.0) { [weak self] in
            self?.handleGracefulStopTimeout(generation: generation)
        }
    }

    func send(command: String, payload: [String: Any] = [:]) {
        guard let process else {
            appendLog("command skipped, helper is not running: \(command)")
            return
        }
        guard lifecycle.handshakeComplete || command == "shutdown" else {
            appendLog("command deferred until helper handshake: \(command)")
            return
        }
        var message: [String: Any] = ["command": command]
        for (key, value) in payload {
            message[key] = value
        }
        do {
            var data = try JSONSerialization.data(withJSONObject: message)
            data.append(Data("\n".utf8))
            try process.send(data)
            appendLog("sent \(command)")
        } catch {
            appendLog("send failed: \(error.localizedDescription)")
        }
    }

    private func consumeStdout(_ data: Data, generation: Int) {
        guard generation == lifecycle.generation else {
            return
        }
        for frame in stdoutFrames.append(data) {
            handleHelperLine(frame, generation: generation)
        }
    }

    private func consumeStderr(_ data: Data, generation: Int) {
        guard generation == lifecycle.generation else {
            return
        }
        for frame in stderrFrames.append(data) {
            if let line = String(data: frame, encoding: .utf8), !line.isEmpty {
                appendLog("stderr: \(line)")
            }
        }
    }

    private func handleHelperLine(_ data: Data, generation: Int) {
        guard
            let object = try? JSONSerialization.jsonObject(with: data),
            let event = object as? [String: Any],
            let type = event["type"] as? String
        else {
            appendLog("invalid helper event")
            return
        }

        if type == "hello" {
            let version = event["protocolVersion"] as? Int
            if lifecycle.handshakeComplete,
               version == supportedHelperProtocolVersion
            {
                appendLog("duplicate helper hello ignored")
                return
            }
            guard lifecycle.acceptHello(generation: generation, version: version) else {
                syncProcessPhase()
                state = .error
                errorMessage = "The helper protocol is incompatible. Reinstall or update Aside, then restart the helper."
                appendLog("incompatible helper protocol \(version.map(String.init) ?? "missing")")
                beginStop(restart: false)
                return
            }
            syncProcessPhase()
            appendLog("helper protocol ready")
            return
        }

        guard lifecycle.handshakeComplete else {
            appendLog("ignored \(type) before helper handshake")
            return
        }

        switch type {
        case "status":
            if let rawState = event["state"] as? String {
                applyStatus(rawState, event: event)
            }
        case "permissions":
            if let values = event["permissions"] as? [String: String] {
                permissions = values
                permissionsReady = !values.isEmpty && values.values.allSatisfy {
                    $0 == "granted"
                }
                appendLog("permissions updated")
            }
        case "dictionary":
            if let values = event["dictionary"] as? [String: Any] {
                dictionary = HelperDictionary(event: values)
                appendLog("dictionary updated")
            }
        case "transcription":
            let text = event["text"] as? String ?? ""
            appendLog("transcribed: \(text)")
        case "config":
            if let values = event["config"] as? [String: Any] {
                config = HelperConfig(event: values)
            }
            appendLog("config reloaded")
        case "capture":
            if let active = event["active"] as? Bool, active {
                captureTarget = event["target"] as? String
            } else {
                captureTarget = nil
            }
            appendLog(captureTarget == nil ? "capture ended" : "capturing hotkey")
        case "error":
            state = .error
            errorMessage = event["message"] as? String ?? "Helper error"
            appendLog("helper error: \(errorMessage ?? "")")
        case "exit":
            appendLog("helper exit event")
        default:
            appendLog("event: \(type)")
        }
    }

    private func applyStatus(_ rawState: String, event: [String: Any]) {
        if let ready = event["modelReady"] as? Bool {
            modelReady = ready
        }
        if let ready = event["permissionsReady"] as? Bool {
            permissionsReady = ready
        }
        if let rawCapture = event["captureState"] as? String {
            captureState = HelperCaptureState(rawValue: rawCapture) ?? .idle
        }
        state = HelperState(rawValue: rawState) ?? .error
        errorMessage = state == .error ? event["message"] as? String : nil
        appendLog("status \(rawState)")
        if rawState == "ready" {
            scheduleProtocolSmokeExit()
        }
    }

    private func handleHandshakeTimeout(generation: Int) {
        guard lifecycle.handshakeExpired(generation: generation) else {
            return
        }
        syncProcessPhase()
        state = .error
        errorMessage = "The helper did not complete its startup handshake. Restart the helper or reinstall Aside."
        appendLog("helper handshake timed out")
        beginStop(restart: false)
    }

    private func handleGracefulStopTimeout(generation: Int) {
        guard lifecycle.gracefulStopExpired(generation: generation) == .terminate else {
            return
        }
        syncProcessPhase()
        appendLog("helper did not exit gracefully; sending terminate")
        process?.requestTermination()
        scheduler(1.0) { [weak self] in
            self?.handleTerminationTimeout(generation: generation)
        }
    }

    private func handleTerminationTimeout(generation: Int) {
        guard lifecycle.terminationExpired(generation: generation) == .forceKill else {
            return
        }
        appendLog("helper ignored terminate; forcing exit")
        process?.forceTermination()
    }

    private func handleTermination(status: Int32, generation: Int) {
        let expected = lifecycle.phase == .stopping || lifecycle.phase == .terminating
        guard let shouldRestart = lifecycle.didExit(generation: generation) else {
            return
        }
        process?.invalidateHandlers()
        process = nil
        isRunning = false
        captureTarget = nil
        captureState = .idle
        syncProcessPhase()
        if !expected, state != .error {
            state = .error
            errorMessage = "The helper exited unexpectedly (status \(status)). Restart the helper to recover."
        } else if state != .error {
            state = .stopped
        }
        appendLog("helper exited \(status)")
        if shouldRestart {
            startHelper()
        } else {
            finishShutdownCompletions()
        }
    }

    private func resetTransientState() {
        stdoutFrames.reset()
        stderrFrames.reset()
        permissions = [:]
        permissionsReady = false
        modelReady = false
        captureTarget = nil
        captureState = .idle
        didScheduleProtocolSmokeExit = false
    }

    private func syncProcessPhase() {
        processPhase = lifecycle.phase
    }

    private func finishShutdownCompletions() {
        let completions = shutdownCompletions
        shutdownCompletions.removeAll()
        for completion in completions {
            completion()
        }
    }

    private func appendLog(_ line: String) {
        eventLog.append(line)
        if eventLog.count > 80 {
            eventLog.removeFirst(eventLog.count - 80)
        }
        if isProtocolSmokeMode {
            let data = Data("[AsideShell] \(line)\n".utf8)
            FileHandle.standardError.write(data)
            if let path = swiftProtocolSmokeLogPath() {
                let url = URL(fileURLWithPath: path)
                if !FileManager.default.fileExists(atPath: url.path) {
                    FileManager.default.createFile(atPath: url.path, contents: nil)
                }
                if let handle = try? FileHandle(forWritingTo: url) {
                    do {
                        try handle.seekToEnd()
                        try handle.write(contentsOf: data)
                        try handle.close()
                    } catch {
                        try? handle.close()
                    }
                }
            }
        }
    }

    private func scheduleProtocolSmokeExit() {
        guard isProtocolSmokeMode, !didScheduleProtocolSmokeExit else {
            return
        }
        didScheduleProtocolSmokeExit = true
        appendLog("protocol smoke passed: helper ready")
        shutdownHelper {
            NSApplication.shared.terminate(nil)
        }
    }
}

struct HelperLaunch {
    let executable: URL
    let arguments: [String]
    let workingDirectory: URL?
    let pythonPath: String?
}

struct HelperConfig {
    var modelSize = "base"
    var language: String?
    var hotkey = HotkeyConfig(modifiers: ["ctrl", "alt"], trigger: "space")
    var toggleHotkey: HotkeyConfig?
    var punctuation = PunctuationConfig()

    init() {}

    init(event: [String: Any]) {
        modelSize = event["modelSize"] as? String ?? "base"
        language = event["language"] as? String
        if let hotkeyEvent = event["hotkey"] as? [String: Any] {
            hotkey = HotkeyConfig(event: hotkeyEvent)
        }
        if let toggleEvent = event["toggleHotkey"] as? [String: Any] {
            toggleHotkey = HotkeyConfig(event: toggleEvent)
        }
        if let punctuationEvent = event["punctuation"] as? [String: Any] {
            punctuation = PunctuationConfig(event: punctuationEvent)
        }
    }
}

struct PunctuationConfig {
    var capitalization = "sentence"
    var smartQuotes = false
    var trailingSpace = true

    init() {}

    init(event: [String: Any]) {
        capitalization = event["capitalization"] as? String ?? "sentence"
        smartQuotes = event["smartQuotes"] as? Bool ?? false
        trailingSpace = event["trailingSpace"] as? Bool ?? true
    }

    var payload: [String: Any] {
        [
            "capitalization": capitalization,
            "smartQuotes": smartQuotes,
            "trailingSpace": trailingSpace,
        ]
    }
}

struct HelperDictionary {
    var hotwords: [String] = []
    var replacements: [ReplacementRule] = []
    var termCount = 0
    var maxTerms = 50
    var overLimit = false

    init() {}

    init(event: [String: Any]) {
        hotwords = event["hotwords"] as? [String] ?? []
        if let rules = event["replacements"] as? [[String: String]] {
            replacements = rules.map {
                ReplacementRule(wrong: $0["wrong"] ?? "", right: $0["right"] ?? "")
            }
        }
        termCount = event["termCount"] as? Int ?? 0
        maxTerms = event["maxTerms"] as? Int ?? 50
        overLimit = event["overLimit"] as? Bool ?? false
    }
}

struct ReplacementRule: Hashable {
    var wrong: String
    var right: String
}

struct HotkeyConfig {
    var modifiers: [String]
    var trigger: String

    init(modifiers: [String], trigger: String) {
        self.modifiers = modifiers
        self.trigger = trigger
    }

    init(event: [String: Any]) {
        modifiers = event["modifiers"] as? [String] ?? []
        trigger = event["trigger"] as? String ?? ""
    }

    var displayParts: [String] {
        modifiers.map { modifier in
            switch modifier {
            case "ctrl": "^"
            case "alt": "Option"
            case "cmd": "Command"
            case "shift": "Shift"
            default: modifier
            }
        } + [trigger.capitalized]
    }

    var displayText: String {
        displayParts.joined(separator: " ")
    }
}

func bundledHelperExecutableURL() -> URL {
    Bundle.main.bundleURL
        .appendingPathComponent("Contents")
        .appendingPathComponent("Helpers")
        .appendingPathComponent("AsideHelper.app")
        .appendingPathComponent("Contents")
        .appendingPathComponent("MacOS")
        .appendingPathComponent("AsideHelper")
}

func processHasArgument(_ name: String) -> Bool {
    ProcessInfo.processInfo.arguments.contains(name)
}

func processArgumentValue(_ name: String) -> String? {
    let args = ProcessInfo.processInfo.arguments
    guard let index = args.firstIndex(of: name) else {
        return nil
    }
    let valueIndex = args.index(after: index)
    guard valueIndex < args.endIndex else {
        return nil
    }
    let value = args[valueIndex]
    return value.isEmpty ? nil : value
}

func swiftProtocolSmokeMode() -> Bool {
    ProcessInfo.processInfo.environment["ASIDE_SWIFTUI_PROTOCOL_SMOKE"] == "1" ||
        processHasArgument("--aside-protocol-smoke")
}

func swiftProtocolSmokeLogPath() -> String? {
    processArgumentValue("--aside-smoke-log") ??
        ProcessInfo.processInfo.environment["ASIDE_SWIFTUI_SMOKE_LOG_PATH"]
}

func resolvedHelperLaunch(environment: [String: String]) -> HelperLaunch {
    let helperExecutable = bundledHelperExecutableURL()
    if FileManager.default.isExecutableFile(atPath: helperExecutable.path) {
        return HelperLaunch(
            executable: helperExecutable,
            arguments: [],
            workingDirectory: Bundle.main.bundleURL,
            pythonPath: nil
        )
    }

    let repoRoot = resolvedRepoRoot(environment: environment)
    let python = resolvedPython(repoRoot: repoRoot, environment: environment)
    return HelperLaunch(
        executable: URL(fileURLWithPath: python),
        arguments: ["-u", "-m", "aside.helper"],
        workingDirectory: URL(fileURLWithPath: repoRoot),
        pythonPath: URL(fileURLWithPath: repoRoot).appendingPathComponent("src").path
    )
}

func resolvedRepoRoot(environment: [String: String]) -> String {
    if let explicit = processArgumentValue("--aside-repo-root") {
        return explicit
    }

    if let explicit = environment["ASIDE_REPO_ROOT"], !explicit.isEmpty {
        return explicit
    }

    let cwd = FileManager.default.currentDirectoryPath
    if FileManager.default.fileExists(atPath: "\(cwd)/src/aside/helper.py") {
        return cwd
    }

    let parent = URL(fileURLWithPath: cwd).deletingLastPathComponent().deletingLastPathComponent().path
    if FileManager.default.fileExists(atPath: "\(parent)/src/aside/helper.py") {
        return parent
    }

    return cwd
}

func resolvedPython(repoRoot: String, environment: [String: String]) -> String {
    if let explicit = processArgumentValue("--aside-python") {
        return explicit
    }

    if let explicit = environment["ASIDE_PYTHON"], !explicit.isEmpty {
        return explicit
    }

    let venvPython = "\(repoRoot)/.venv/bin/python3"
    if FileManager.default.isExecutableFile(atPath: venvPython) {
        return venvPython
    }

    return "/usr/bin/python3"
}
