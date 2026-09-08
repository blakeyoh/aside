import Foundation

let supportedHelperProtocolVersion = 1

struct LineFrameDecoder {
    private(set) var remainder = Data()

    mutating func append(_ data: Data) -> [Data] {
        remainder.append(data)
        var frames: [Data] = []
        while let newline = remainder.firstIndex(of: 10) {
            let frame = Data(remainder[..<newline])
            remainder.removeSubrange(...newline)
            if !frame.isEmpty {
                frames.append(frame)
            }
        }
        return frames
    }

    mutating func reset() {
        remainder.removeAll(keepingCapacity: false)
    }
}
enum HelperProcessPhase: Equatable {
    case stopped
    case starting
    case awaitingHandshake
    case running
    case stopping
    case terminating
    case failed
}

enum HelperStopEscalation: Equatable {
    case none
    case terminate
    case forceKill
}

struct HelperLifecycle {
    private(set) var generation = 0
    private(set) var phase: HelperProcessPhase = .stopped
    private(set) var restartPending = false
    private(set) var handshakeComplete = false

    mutating func beginStart() -> Int {
        generation += 1
        phase = .starting
        restartPending = false
        handshakeComplete = false
        return generation
    }

    mutating func didLaunch(generation candidate: Int) -> Bool {
        guard candidate == generation, phase == .starting else {
            return false
        }
        phase = .awaitingHandshake
        return true
    }

    mutating func acceptHello(generation candidate: Int, version: Int?) -> Bool {
        guard candidate == generation, phase == .awaitingHandshake else {
            return false
        }
        guard version == supportedHelperProtocolVersion else {
            phase = .failed
            return false
        }
        handshakeComplete = true
        phase = .running
        return true
    }

    mutating func requestStop(restart: Bool) -> Bool {
        restartPending = restartPending || restart
        switch phase {
        case .stopped:
            return false
        case .stopping, .terminating:
            return false
        default:
            phase = .stopping
            return true
        }
    }

    mutating func handshakeExpired(generation candidate: Int) -> Bool {
        guard candidate == generation,
              phase == .awaitingHandshake,
              !handshakeComplete
        else {
            return false
        }
        phase = .failed
        return true
    }

    mutating func gracefulStopExpired(generation candidate: Int) -> HelperStopEscalation {
        guard candidate == generation, phase == .stopping else {
            return .none
        }
        phase = .terminating
        return .terminate
    }

    mutating func terminationExpired(generation candidate: Int) -> HelperStopEscalation {
        guard candidate == generation, phase == .terminating else {
            return .none
        }
        return .forceKill
    }

    mutating func didExit(generation candidate: Int) -> Bool? {
        guard candidate == generation else {
            return nil
        }
        let shouldRestart = restartPending
        phase = .stopped
        restartPending = false
        handshakeComplete = false
        return shouldRestart
    }

    mutating func didFailToLaunch(generation candidate: Int) -> Bool {
        guard candidate == generation else {
            return false
        }
        phase = .failed
        return true
    }
}
