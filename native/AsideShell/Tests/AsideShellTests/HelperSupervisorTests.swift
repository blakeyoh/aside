import Foundation
import XCTest
@testable import AsideShell

private final class FakeHelperProcess: HelperProcessDriving {
    var processIdentifier: Int32 = 42
    var isRunning = false
    var stdoutHandler: ((Data) -> Void)?
    var stderrHandler: ((Data) -> Void)?
    var exitHandler: ((Int32) -> Void)?
    var sent: [Data] = []
    var terminationRequests = 0
    var forceTerminationRequests = 0
    var inputClosed = false
    var runError: Error?

    func run() throws {
        if let runError {
            throw runError
        }
        isRunning = true
    }

    func send(_ data: Data) throws {
        sent.append(data)
    }

    func closeInput() {
        inputClosed = true
    }

    func requestTermination() {
        terminationRequests += 1
    }

    func forceTermination() {
        forceTerminationRequests += 1
    }

    func invalidateHandlers() {
        stdoutHandler = nil
        stderrHandler = nil
        exitHandler = nil
    }

    func emitStdout(_ value: String) {
        stdoutHandler?(Data(value.utf8))
    }

    func emitStderr(_ value: String) {
        stderrHandler?(Data(value.utf8))
    }

    func exit(status: Int32) {
        isRunning = false
        exitHandler?(status)
    }

    var sentText: String {
        sent.compactMap { String(data: $0, encoding: .utf8) }.joined()
    }
}

@MainActor
private final class ManualScheduler {
    private var actions: [@MainActor () -> Void] = []

    func schedule(after _: TimeInterval, action: @escaping @MainActor () -> Void) {
        actions.append(action)
    }

    func runNext() {
        guard !actions.isEmpty else {
            XCTFail("No scheduled action available")
            return
        }
        actions.removeFirst()()
    }
}

@MainActor
final class HelperSupervisorTests: XCTestCase {
    private func makeSupervisor() -> (
        HelperSupervisor,
        ManualScheduler,
        () -> [FakeHelperProcess]
    ) {
        let scheduler = ManualScheduler()
        var processes: [FakeHelperProcess] = []
        let supervisor = HelperSupervisor(
            processFactory: { _, _ in
                let process = FakeHelperProcess()
                processes.append(process)
                return process
            },
            scheduler: scheduler.schedule,
            launchResolver: { _ in
                HelperLaunch(
                    executable: URL(fileURLWithPath: "/bin/echo"),
                    arguments: [],
                    workingDirectory: nil,
                    pythonPath: nil
                )
            },
            environmentProvider: { [:] },
            executableCheck: { _ in true },
            protocolSmokeMode: { false }
        )
        return (supervisor, scheduler, { processes })
    }

    private func completeHandshake(_ process: FakeHelperProcess) async {
        process.emitStdout(
            "{\"type\":\"hello\",\"protocolVersion\":1}\n"
        )
        await Task.yield()
    }

    func testFragmentedFramesWaitForAValidHandshake() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let process = processes()[0]

        process.emitStdout("{\"type\":\"hel")
        await Task.yield()
        XCTAssertEqual(supervisor.processPhase, .awaitingHandshake)

        process.emitStdout(
            "lo\",\"protocolVersion\":1}\n" +
                "{\"type\":\"status\",\"state\":\"ready\"," +
                "\"modelReady\":true,\"permissionsReady\":true," +
                "\"captureState\":\"idle\"}\n"
        )
        await Task.yield()

        XCTAssertEqual(supervisor.processPhase, .running)
        XCTAssertEqual(supervisor.state, .ready)
        XCTAssertTrue(supervisor.modelReady)
        XCTAssertTrue(supervisor.permissionsReady)
    }

    func testMalformedAndUnknownEventsAreContained() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let process = processes()[0]
        await completeHandshake(process)

        process.emitStdout("not-json\n{\"type\":\"futureEvent\"}\n")
        await Task.yield()

        XCTAssertTrue(supervisor.eventLog.contains("invalid helper event"))
        XCTAssertTrue(supervisor.eventLog.contains("event: futureEvent"))
        XCTAssertEqual(supervisor.processPhase, .running)
    }

    func testIncompatibleProtocolStopsWithRecoveryMessage() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let process = processes()[0]

        process.emitStdout(
            "{\"type\":\"hello\",\"protocolVersion\":999}\n"
        )
        await Task.yield()

        XCTAssertEqual(supervisor.state, .error)
        XCTAssertTrue(supervisor.errorMessage?.contains("incompatible") == true)
        XCTAssertEqual(supervisor.processPhase, .stopping)
        XCTAssertTrue(process.sentText.contains("shutdown"))
        XCTAssertTrue(process.inputClosed)
    }

    func testHandshakeTimeoutStopsTheCurrentProcess() {
        let (supervisor, scheduler, processes) = makeSupervisor()
        supervisor.startHelper()

        scheduler.runNext()

        XCTAssertEqual(supervisor.state, .error)
        XCTAssertTrue(supervisor.errorMessage?.contains("handshake") == true)
        XCTAssertEqual(supervisor.processPhase, .stopping)
        XCTAssertTrue(processes()[0].sentText.contains("shutdown"))
    }

    func testRestartLaunchesSuccessorOnlyAfterConfirmedExit() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let first = processes()[0]
        await completeHandshake(first)

        supervisor.restartHelper()

        XCTAssertEqual(processes().count, 1)
        XCTAssertEqual(supervisor.processPhase, .stopping)
        first.exit(status: 0)
        await Task.yield()

        XCTAssertEqual(processes().count, 2)
        XCTAssertEqual(supervisor.processPhase, .awaitingHandshake)
    }

    func testStaleCallbackCannotMutateReplacement() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let first = processes()[0]
        await completeHandshake(first)
        let staleOutput = first.stdoutHandler
        supervisor.restartHelper()
        first.exit(status: 0)
        await Task.yield()

        staleOutput?(Data(
            "{\"type\":\"status\",\"state\":\"recording\"}\n".utf8
        ))
        await Task.yield()

        XCTAssertEqual(supervisor.processPhase, .awaitingHandshake)
        XCTAssertEqual(supervisor.state, .loading)
        XCTAssertEqual(supervisor.captureState, .idle)
    }

    func testGracefulShutdownEscalatesAndWaitsForExit() async {
        let (supervisor, scheduler, processes) = makeSupervisor()
        supervisor.startHelper()
        let process = processes()[0]
        await completeHandshake(process)

        supervisor.shutdownHelper()
        XCTAssertEqual(supervisor.processPhase, .stopping)
        XCTAssertEqual(process.terminationRequests, 0)
        scheduler.runNext() // completed handshake timer, now inert
        scheduler.runNext() // graceful-exit deadline
        XCTAssertEqual(process.terminationRequests, 1)
        scheduler.runNext() // terminate deadline
        XCTAssertEqual(process.forceTerminationRequests, 1)
        XCTAssertTrue(supervisor.isRunning)

        process.exit(status: 9)
        await Task.yield()
        XCTAssertEqual(supervisor.processPhase, .stopped)
        XCTAssertFalse(supervisor.isRunning)
    }

    func testShutdownCompletionWaitsForConfirmedExit() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let process = processes()[0]
        await completeHandshake(process)
        var completionCalled = false

        supervisor.shutdownHelper {
            completionCalled = true
        }

        XCTAssertFalse(completionCalled)
        process.exit(status: 0)
        await Task.yield()
        XCTAssertTrue(completionCalled)
    }

    func testShutdownDuringRecordingClearsCaptureAfterExit() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let process = processes()[0]
        await completeHandshake(process)
        process.emitStdout(
            "{\"type\":\"status\",\"state\":\"recording\"," +
                "\"modelReady\":true,\"permissionsReady\":true," +
                "\"captureState\":\"recording\"}\n"
        )
        await Task.yield()
        XCTAssertEqual(supervisor.captureState, .recording)

        supervisor.shutdownHelper()
        XCTAssertEqual(supervisor.captureState, .recording)
        process.exit(status: 0)
        await Task.yield()

        XCTAssertEqual(supervisor.captureState, .idle)
        XCTAssertEqual(supervisor.state, .stopped)
    }

    func testUnexpectedExitIsActionable() async {
        let (supervisor, _, processes) = makeSupervisor()
        supervisor.startHelper()
        let process = processes()[0]
        await completeHandshake(process)

        process.exit(status: 17)
        await Task.yield()

        XCTAssertEqual(supervisor.state, .error)
        XCTAssertTrue(supervisor.errorMessage?.contains("17") == true)
        XCTAssertEqual(supervisor.processPhase, .stopped)
    }
}
