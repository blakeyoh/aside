import Darwin
import Foundation

protocol HelperProcessDriving: AnyObject {
    var processIdentifier: Int32 { get }
    var isRunning: Bool { get }
    var stdoutHandler: ((Data) -> Void)? { get set }
    var stderrHandler: ((Data) -> Void)? { get set }
    var exitHandler: ((Int32) -> Void)? { get set }

    func run() throws
    func send(_ data: Data) throws
    func closeInput()
    func requestTermination()
    func forceTermination()
    func invalidateHandlers()
}

final class FoundationHelperProcess: HelperProcessDriving {
    private let process = Process()
    private let stdinPipe = Pipe()
    private let stdoutPipe = Pipe()
    private let stderrPipe = Pipe()

    var stdoutHandler: ((Data) -> Void)?
    var stderrHandler: ((Data) -> Void)?
    var exitHandler: ((Int32) -> Void)?

    var processIdentifier: Int32 {
        process.processIdentifier
    }

    var isRunning: Bool {
        process.isRunning
    }

    init(launch: HelperLaunch, environment: [String: String]) {
        process.executableURL = launch.executable
        process.arguments = launch.arguments
        process.currentDirectoryURL = launch.workingDirectory
        process.environment = environment
        process.standardInput = stdinPipe
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            self?.stdoutHandler?(data)
        }
        stderrPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            self?.stderrHandler?(data)
        }
        process.terminationHandler = { [weak self] finishedProcess in
            self?.exitHandler?(finishedProcess.terminationStatus)
        }
    }

    func run() throws {
        try process.run()
    }

    func send(_ data: Data) throws {
        try stdinPipe.fileHandleForWriting.write(contentsOf: data)
    }

    func closeInput() {
        try? stdinPipe.fileHandleForWriting.close()
    }

    func requestTermination() {
        if process.isRunning {
            process.terminate()
        }
    }

    func forceTermination() {
        guard process.isRunning, process.processIdentifier > 0 else {
            return
        }
        kill(process.processIdentifier, SIGKILL)
    }

    func invalidateHandlers() {
        process.terminationHandler = nil
        stdoutPipe.fileHandleForReading.readabilityHandler = nil
        stderrPipe.fileHandleForReading.readabilityHandler = nil
        stdoutHandler = nil
        stderrHandler = nil
        exitHandler = nil
    }
}
