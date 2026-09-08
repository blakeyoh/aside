import Foundation
import XCTest
@testable import AsideShell

final class HelperLifecycleTests: XCTestCase {
    func testLineDecoderHandlesFragmentedAndMultipleFrames() {
        var decoder = LineFrameDecoder()

        XCTAssertEqual(decoder.append(Data("{\"type\":\"hel".utf8)), [])
        let frames = decoder.append(
            Data("lo\"}\n{\"type\":\"status\"}\ntail".utf8)
        )

        XCTAssertEqual(frames.count, 2)
        XCTAssertEqual(String(data: frames[0], encoding: .utf8), #"{"type":"hello"}"#)
        XCTAssertEqual(String(data: frames[1], encoding: .utf8), #"{"type":"status"}"#)
        XCTAssertEqual(String(data: decoder.remainder, encoding: .utf8), "tail")
    }

    func testResetDropsPartialFrameBetweenProcesses() {
        var decoder = LineFrameDecoder()
        XCTAssertTrue(decoder.append(Data("stale".utf8)).isEmpty)

        decoder.reset()
        let frames = decoder.append(Data("fresh\n".utf8))

        XCTAssertEqual(frames, [Data("fresh".utf8)])
    }

    func testHandshakeRequiresMatchingGenerationAndVersion() {
        var lifecycle = HelperLifecycle()
        let generation = lifecycle.beginStart()
        XCTAssertTrue(lifecycle.didLaunch(generation: generation))

        XCTAssertFalse(
            lifecycle.acceptHello(
                generation: generation - 1,
                version: supportedHelperProtocolVersion
            )
        )
        XCTAssertFalse(lifecycle.handshakeComplete)
        XCTAssertTrue(
            lifecycle.acceptHello(
                generation: generation,
                version: supportedHelperProtocolVersion
            )
        )
        XCTAssertEqual(lifecycle.phase, .running)
    }

    func testIncompatibleProtocolFailsHandshake() {
        var lifecycle = HelperLifecycle()
        let generation = lifecycle.beginStart()
        XCTAssertTrue(lifecycle.didLaunch(generation: generation))

        XCTAssertFalse(lifecycle.acceptHello(generation: generation, version: 999))
        XCTAssertEqual(lifecycle.phase, .failed)
    }

    func testHandshakeTimeoutIgnoresStaleGeneration() {
        var lifecycle = HelperLifecycle()
        let oldGeneration = lifecycle.beginStart()
        XCTAssertTrue(lifecycle.didLaunch(generation: oldGeneration))
        let currentGeneration = lifecycle.beginStart()
        XCTAssertTrue(lifecycle.didLaunch(generation: currentGeneration))

        XCTAssertFalse(lifecycle.handshakeExpired(generation: oldGeneration))
        XCTAssertEqual(lifecycle.phase, .awaitingHandshake)
        XCTAssertTrue(lifecycle.handshakeExpired(generation: currentGeneration))
        XCTAssertEqual(lifecycle.phase, .failed)
    }

    func testRestartWaitsForExitAndRejectsOldExit() {
        var lifecycle = HelperLifecycle()
        let generation = lifecycle.beginStart()
        XCTAssertTrue(lifecycle.didLaunch(generation: generation))
        XCTAssertTrue(
            lifecycle.acceptHello(
                generation: generation,
                version: supportedHelperProtocolVersion
            )
        )

        XCTAssertTrue(lifecycle.requestStop(restart: true))
        XCTAssertEqual(lifecycle.phase, .stopping)
        XCTAssertNil(lifecycle.didExit(generation: generation - 1))
        XCTAssertEqual(lifecycle.phase, .stopping)
        XCTAssertEqual(lifecycle.didExit(generation: generation), true)
        XCTAssertEqual(lifecycle.phase, .stopped)
    }

    func testExplicitShutdownCancelsAPendingRestart() {
        var lifecycle = HelperLifecycle()
        let generation = lifecycle.beginStart()
        XCTAssertTrue(lifecycle.didLaunch(generation: generation))
        XCTAssertTrue(lifecycle.requestStop(restart: true))

        XCTAssertFalse(lifecycle.requestStop(restart: false))

        XCTAssertEqual(lifecycle.didExit(generation: generation), false)
    }

    func testShutdownEscalatesOnlyForCurrentGeneration() {
        var lifecycle = HelperLifecycle()
        let generation = lifecycle.beginStart()
        XCTAssertTrue(lifecycle.didLaunch(generation: generation))
        XCTAssertTrue(lifecycle.requestStop(restart: false))

        XCTAssertEqual(
            lifecycle.gracefulStopExpired(generation: generation - 1),
            .none
        )
        XCTAssertEqual(
            lifecycle.gracefulStopExpired(generation: generation),
            .terminate
        )
        XCTAssertEqual(
            lifecycle.terminationExpired(generation: generation),
            .forceKill
        )
    }
}
