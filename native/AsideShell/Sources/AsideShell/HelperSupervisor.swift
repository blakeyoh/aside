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

    var helperDescription: String {
        let env = ProcessInfo.processInfo.environment
        let repoRoot = resolvedRepoRoot(environment: env)
        let python = resolvedPython(repoRoot: repoRoot, environment: env)
        return "\(python) -m aside.helper"
    }

    func startHelper() {
        guard process == nil else {
            return
        }

        let env = ProcessInfo.processInfo.environment
        let repoRoot = resolvedRepoRoot(environment: env)
        let pythonPath = resolvedPython(repoRoot: repoRoot, environment: env)

        guard FileManager.default.isExecutableFile(atPath: pythonPath) else {
            state = .error
            errorMessage = "Python helper is not executable at \(pythonPath). Set ASIDE_PYTHON or run from the repo root after setup.sh."
            appendLog("launch failed: \(pythonPath)")
            return
        }

        let process = Process()
        let stdinPipe = Pipe()
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()

        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = ["-u", "-m", "aside.helper"]
        process.currentDirectoryURL = URL(fileURLWithPath: repoRoot)

        var childEnvironment = env
        childEnvironment["PYTHONUNBUFFERED"] = "1"
        let srcPath = URL(fileURLWithPath: repoRoot).appendingPathComponent("src").path
        if let existing = childEnvironment["PYTHONPATH"], !existing.isEmpty {
            childEnvironment["PYTHONPATH"] = "\(srcPath):\(existing)"
        } else {
            childEnvironment["PYTHONPATH"] = srcPath
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
            Task { @MainActor in
                self?.consumeStdout(data)
            }
        }

        stderrPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            Task { @MainActor in
                self?.consumeStderr(data)
            }
        }

        process.terminationHandler = { [weak self] finishedProcess in
            Task { @MainActor in
                self?.handleTermination(status: finishedProcess.terminationStatus)
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
    }
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

func resolvedRepoRoot(environment: [String: String]) -> String {
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
    if let explicit = environment["ASIDE_PYTHON"], !explicit.isEmpty {
        return explicit
    }

    let venvPython = "\(repoRoot)/.venv/bin/python3"
    if FileManager.default.isExecutableFile(atPath: venvPython) {
        return venvPython
    }

    return "/usr/bin/python3"
}
