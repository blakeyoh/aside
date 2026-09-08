import AppKit
import Foundation
import SwiftUI

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

    private var process: Process?
    private var stdinPipe: Pipe?
    private var stdoutRemainder = Data()
    private var stderrRemainder = Data()
    private var didScheduleProtocolSmokeExit = false

    private var isProtocolSmokeMode: Bool {
        swiftProtocolSmokeMode()
    }

    var helperDescription: String {
        let launch = resolvedHelperLaunch(environment: ProcessInfo.processInfo.environment)
        return ([launch.executable.path] + launch.arguments).joined(separator: " ")
    }

    func startHelper() {
        guard process == nil else {
            return
        }

        let launch = resolvedHelperLaunch(environment: ProcessInfo.processInfo.environment)
        let executablePath = launch.executable.path

        guard FileManager.default.isExecutableFile(atPath: executablePath) else {
            state = .error
            errorMessage = "Helper is not executable at \(executablePath). Set ASIDE_PYTHON or run from the repo root after setup.sh."
            appendLog("launch failed: \(executablePath)")
            return
        }

        let process = Process()
        let stdinPipe = Pipe()
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()

        process.executableURL = launch.executable
        process.arguments = launch.arguments
        process.currentDirectoryURL = launch.workingDirectory

        var childEnvironment = ProcessInfo.processInfo.environment
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
        process.environment = childEnvironment

        process.standardInput = stdinPipe
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            guard let supervisor = self else {
                return
            }
            Task { @MainActor [supervisor, data] in
                supervisor.consumeStdout(data)
            }
        }

        stderrPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            guard let supervisor = self else {
                return
            }
            Task { @MainActor [supervisor, data] in
                supervisor.consumeStderr(data)
            }
        }

        process.terminationHandler = { [weak self] finishedProcess in
            let status = finishedProcess.terminationStatus
            guard let supervisor = self else {
                return
            }
            Task { @MainActor [supervisor, status] in
                supervisor.handleTermination(status: status)
            }
        }

        do {
            try process.run()
            self.process = process
            self.stdinPipe = stdinPipe
            state = .loading
            errorMessage = nil
            isRunning = true
            appendLog("launched helper pid \(process.processIdentifier)")
        } catch {
            state = .error
            errorMessage = "Could not launch helper: \(error.localizedDescription)"
            appendLog("launch error: \(error.localizedDescription)")
        }
    }

    func restartHelper() {
        shutdownHelper()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
            self.startHelper()
        }
    }

    func shutdownHelper() {
        guard let process else {
            return
        }
        send(command: "shutdown")
        stdinPipe?.fileHandleForWriting.closeFile()
        process.terminate()
        cleanupPipes()
        self.process = nil
        self.stdinPipe = nil
        isRunning = false
        state = .stopped
        appendLog("shutdown requested")
    }

    func send(command: String, payload: [String: Any] = [:]) {
        guard let stdinPipe else {
            appendLog("command skipped, helper is not running: \(command)")
            return
        }
        var message: [String: Any] = ["command": command]
        for (key, value) in payload {
            message[key] = value
        }
        do {
            let data = try JSONSerialization.data(withJSONObject: message)
            stdinPipe.fileHandleForWriting.write(data)
            stdinPipe.fileHandleForWriting.write(Data("\n".utf8))
            appendLog("sent \(command)")
        } catch {
            appendLog("send failed: \(error.localizedDescription)")
        }
    }

    private func consumeStdout(_ data: Data) {
        stdoutRemainder.append(data)
        while let newline = stdoutRemainder.firstIndex(of: 10) {
            let lineData = stdoutRemainder[..<newline]
            stdoutRemainder.removeSubrange(...newline)
            guard !lineData.isEmpty else {
                continue
            }
            handleHelperLine(Data(lineData))
        }
    }

    private func consumeStderr(_ data: Data) {
        stderrRemainder.append(data)
        while let newline = stderrRemainder.firstIndex(of: 10) {
            let lineData = stderrRemainder[..<newline]
            stderrRemainder.removeSubrange(...newline)
            if let line = String(data: lineData, encoding: .utf8), !line.isEmpty {
                appendLog("stderr: \(line)")
            }
        }
    }

    private func handleHelperLine(_ data: Data) {
        guard
            let object = try? JSONSerialization.jsonObject(with: data),
            let event = object as? [String: Any],
            let type = event["type"] as? String
        else {
            appendLog("invalid helper event")
            return
        }

        switch type {
        case "hello":
            appendLog("helper protocol ready")
        case "status":
            if let rawState = event["state"] as? String {
                applyStatus(rawState, message: event["message"] as? String)
            }
        case "permissions":
            if let values = event["permissions"] as? [String: String] {
                permissions = values
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

    private func applyStatus(_ rawState: String, message: String?) {
        state = HelperState(rawValue: rawState) ?? .error
        errorMessage = state == .error ? message : nil
        appendLog("status \(rawState)")
        if rawState == "ready" {
            scheduleProtocolSmokeExit()
        }
    }

    private func handleTermination(status: Int32) {
        cleanupPipes()
        process = nil
        stdinPipe = nil
        isRunning = false
        if state != .error {
            state = .stopped
        }
        appendLog("helper exited \(status)")
    }

    private func cleanupPipes() {
        process?.terminationHandler = nil
        if let stdout = process?.standardOutput as? Pipe {
            stdout.fileHandleForReading.readabilityHandler = nil
        }
        if let stderr = process?.standardError as? Pipe {
            stderr.fileHandleForReading.readabilityHandler = nil
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
        send(command: "shutdown")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
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
