import AppKit
import SwiftUI

enum HelperState: String {
    case loading
    case ready
    case recording
    case transcribing
    case error
    case stopped

    var title: String {
        switch self {
        case .loading: "Loading"
        case .ready: "Ready"
        case .recording: "Recording"
        case .transcribing: "Transcribing"
        case .error: "Needs attention"
        case .stopped: "Stopped"
        }
    }

    var color: Color {
        switch self {
        case .loading: AsideDesign.blue
        case .ready: AsideDesign.green
        case .recording: AsideDesign.amber
        case .transcribing: AsideDesign.blue
        case .error: AsideDesign.red
        case .stopped: AsideDesign.slate
        }
    }

    var systemImage: String {
        switch self {
        case .loading: "arrow.triangle.2.circlepath"
        case .ready: "checkmark.circle.fill"
        case .recording: "waveform"
        case .transcribing: "text.bubble.fill"
        case .error: "exclamationmark.triangle.fill"
        case .stopped: "pause.circle.fill"
        }
    }

    var menuBarSystemImage: String {
        switch self {
        case .recording: "waveform.circle.fill"
        case .transcribing: "text.bubble.fill"
        case .error: "exclamationmark.triangle.fill"
        default: "a.circle"
        }
    }
}

enum AsideDesign {
    static let graphite = Color(red: 0.12, green: 0.14, blue: 0.17)
    static let slate = Color(red: 0.40, green: 0.44, blue: 0.49)
    static let offWhite = Color(red: 0.97, green: 0.96, blue: 0.95)
    static let mist = Color(red: 0.93, green: 0.94, blue: 0.95)
    static let blue = Color(red: 0.37, green: 0.48, blue: 0.90)
    static let amber = Color(red: 0.88, green: 0.63, blue: 0.29)
    static let green = Color(red: 0.37, green: 0.64, blue: 0.54)
    static let red = Color(red: 0.85, green: 0.22, blue: 0.22)
    static let radius: CGFloat = 8
    static let spacing4: CGFloat = 4
    static let spacing8: CGFloat = 8
    static let spacing12: CGFloat = 12
    static let spacing16: CGFloat = 16
    static let spacing24: CGFloat = 24
    static let spacing32: CGFloat = 32
}

let modelOptions = ["tiny", "base", "small", "medium", "large-v3"]
let modelLabels = [
    "tiny": "Fastest, lower accuracy",
    "base": "Balanced, recommended",
    "small": "Better accuracy",
    "medium": "High accuracy",
    "large-v3": "Best accuracy",
]
let languageOptions: [(String, String?)] = [
    ("Auto-detect", nil),
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
]

enum SidebarSection: String, CaseIterable {
    case general = "General"
    case dictation = "Dictation"
    case hotkey = "Hotkey"
    case permissions = "Permissions"
    case localModel = "Local Model"
    case dictionary = "Dictionary"
    case voiceCommands = "Voice Commands"
    case tutorial = "Practice"
    case advanced = "Advanced"
    case about = "About"

    var systemImage: String {
        switch self {
        case .general: "gearshape"
        case .dictation: "mic"
        case .hotkey: "command"
        case .permissions: "hand.raised"
        case .localModel: "cpu"
        case .dictionary: "textformat"
        case .voiceCommands: "waveform.path"
        case .tutorial: "target"
        case .advanced: "slider.horizontal.3"
        case .about: "info.circle"
        }
    }
}

@main
struct AsideShellApp: App {
    @StateObject private var supervisor = HelperSupervisor()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(supervisor)
                .frame(minWidth: 860, minHeight: 650)
                .onAppear {
                    NSApplication.shared.setActivationPolicy(.regular)
                    NSApplication.shared.activate(ignoringOtherApps: true)
                    supervisor.startHelper()
                }
                .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in
                    supervisor.shutdownHelper()
                }
        }
        .windowStyle(.hiddenTitleBar)
        .commands {
            CommandGroup(replacing: .appTermination) {
                Button("Quit Aside") {
                    supervisor.shutdownHelper()
                    NSApplication.shared.terminate(nil)
                }
                .keyboardShortcut("q")
            }
        }

        MenuBarExtra("Aside", systemImage: supervisor.state.menuBarSystemImage) {
            MenuBarContent()
                .environmentObject(supervisor)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject private var supervisor: HelperSupervisor
    @State private var selectedSection: SidebarSection = .general

    var body: some View {
        HStack(spacing: 0) {
            SidebarView(selectedSection: $selectedSection)

            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    HeaderView()
                    StatusPanel()
                    SectionContent(section: $selectedSection)
                }
                .padding(28)
            }
            .background(AsideDesign.offWhite)
        }
    }
}

struct SidebarView: View {
    @Binding var selectedSection: SidebarSection

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(SidebarSection.allCases, id: \.self) { section in
                Button {
                    selectedSection = section
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: section.systemImage)
                            .frame(width: 18)
                        Text(section.rawValue)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .sidebarRow(selected: selectedSection == section)
                }
                .buttonStyle(.plain)
            }

            Spacer()
        }
        .padding(.top, 58)
        .padding(.horizontal, 18)
        .padding(.bottom, 18)
        .frame(width: 205)
        .background(.regularMaterial)
    }
}

struct SectionContent: View {
    @Binding var section: SidebarSection

    var body: some View {
        switch section {
        case .general:
            PrivacyStrip()
            GeneralPanel(goTo: { section = $0 })
        case .dictation:
            DictationPanel()
            ControlsPanel()
            LogPanel()
        case .hotkey:
            HotkeyPanel()
            LogPanel()
        case .permissions:
            OnboardingPanel {
                section = .general
            }
            PermissionPanel()
        case .localModel:
            LocalModelPanel()
            LogPanel()
        case .dictionary:
            DictionaryPanel()
        case .voiceCommands:
            VoiceCommandsPanel()
        case .tutorial:
            TutorialPanel()
        case .advanced:
            AdvancedPanel()
        case .about:
            AboutPanel()
        }
    }
}

struct HeaderView: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        HStack(spacing: 16) {
            AppLogoView()
            .frame(width: 64, height: 64)

            VStack(alignment: .leading, spacing: 4) {
                Text("Aside")
                    .font(.system(size: 30, weight: .bold))
                Text("Private voice dictation for Mac")
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
    }
}

struct AppLogoView: View {
    private var logo: NSImage? {
        let repoRoot = resolvedRepoRoot(environment: ProcessInfo.processInfo.environment)
        return NSImage(contentsOfFile: "\(repoRoot)/assets/NEW-aside-logo.png")
    }

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 13, style: .continuous)
                .fill(AsideDesign.graphite)
            if let logo {
                Image(nsImage: logo)
                    .resizable()
                    .scaledToFit()
                    .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
            } else {
                Image(systemName: "waveform")
                    .font(.system(size: 30, weight: .semibold))
                    .foregroundStyle(.white)
            }
        }
    }
}

struct StatusPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label(supervisor.state.title, systemImage: supervisor.state.systemImage)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundStyle(supervisor.state.color)
                Spacer()
                StatusBadge(text: supervisor.isRunning ? "Helper running" : "Helper stopped", color: supervisor.isRunning ? AsideDesign.green : AsideDesign.slate)
            }

            if let message = supervisor.errorMessage, !message.isEmpty {
                Text(message)
                    .font(.callout)
                    .foregroundStyle(AsideDesign.red)
            } else {
                Text("Audio stays on this Mac. No cloud. No telemetry.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
        }
        .panel()
    }
}

struct PrivacyStrip: View {
    var body: some View {
        HStack(spacing: 12) {
            PrivacyPill(icon: "display", title: "Audio stays on this Mac", caption: "Processed locally")
            PrivacyPill(icon: "leaf", title: "No cloud. No telemetry.", caption: "Your data is yours")
            PrivacyPill(icon: "cpu", title: "Local model ready", caption: "Whisper")
            PrivacyPill(icon: "wifi.slash", title: "Zero network", caption: "Works offline")
        }
        .padding(14)
        .background(AsideDesign.green.opacity(0.10), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous)
                .stroke(AsideDesign.green.opacity(0.20))
        )
    }
}

struct PrivacyPill: View {
    let icon: String
    let title: String
    let caption: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(AsideDesign.green)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption.weight(.semibold))
                Text(caption)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct GeneralPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor
    let goTo: (SidebarSection) -> Void

    private var grantedPermissions: Int {
        ["microphone", "accessibility", "inputMonitoring"].filter {
            supervisor.permissions[$0] == "granted"
        }.count
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Ready to Dictate")
                        .font(.headline)
                    Text("Hold your shortcut, speak, then release.")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                KeycapRow(hotkey: supervisor.config.hotkey)
            }

            HStack(spacing: 10) {
                SummaryTile(title: supervisor.state.title, subtitle: "Helper state", icon: supervisor.state.systemImage, color: supervisor.state.color)
                SummaryTile(title: supervisor.config.modelSize, subtitle: "Local model", icon: "cpu", color: AsideDesign.blue)
                SummaryTile(title: "\(grantedPermissions)/3", subtitle: "Permissions", icon: "hand.raised", color: grantedPermissions == 3 ? AsideDesign.green : AsideDesign.amber)
            }

            HStack {
                Button {
                    goTo(.dictation)
                } label: {
                    Label("Dictation", systemImage: "mic.fill")
                }
                Button {
                    goTo(.dictionary)
                } label: {
                    Label("Dictionary", systemImage: "textformat")
                }
                Button {
                    goTo(.tutorial)
                } label: {
                    Label("Practice", systemImage: "target")
                }
                Spacer()
            }
        }
        .panel()
    }
}

struct SummaryTile: View {
    let title: String
    let subtitle: String
    let icon: String
    let color: Color

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(color)
                .frame(width: 24)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(1)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
        .padding(11)
        .frame(maxWidth: .infinity, minHeight: 64, alignment: .leading)
        .background(AsideDesign.mist.opacity(0.48), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
    }
}

struct DictationPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor
    @State private var toggleMode = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Dictation")
                    .font(.headline)
                Spacer()
                Picker("Mode", selection: $toggleMode) {
                    Text("Push-to-talk").tag(false)
                    Text("Toggle").tag(true)
                }
                .pickerStyle(.segmented)
                .frame(width: 220)
            }

            HStack(alignment: .center, spacing: 12) {
                Text(toggleMode ? "Press" : "Hold")
                    .font(.system(size: 20, weight: .bold))
                KeycapRow(hotkey: toggleMode ? supervisor.config.toggleHotkey : supervisor.config.hotkey)
                Text(toggleMode ? "to toggle dictation" : "to dictate")
                    .font(.system(size: 20, weight: .bold))
                Spacer()
            }

            Text(toggleMode ? "Press once to start, press again to stop." : "Hold the keys to speak. Release to transcribe wherever the cursor is.")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .panel()
    }
}

struct HotkeyPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Hotkey")
                .font(.headline)
            SettingRow(title: "Push-to-talk", subtitle: "Hold to dictate.", trailing: AnyView(
                HStack {
                    KeycapRow(hotkey: supervisor.config.hotkey)
                    Button(supervisor.captureTarget == "hotkey" ? "Cancel" : "Change") {
                        if supervisor.captureTarget == "hotkey" {
                            supervisor.send(command: "cancelHotkeyCapture")
                        } else {
                            supervisor.send(command: "startHotkeyCapture", payload: ["target": "hotkey"])
                        }
                    }
                }
            ))
            SettingRow(title: "Toggle", subtitle: "Press once to start and again to stop.", trailing: AnyView(
                HStack {
                    if let toggleHotkey = supervisor.config.toggleHotkey {
                        KeycapRow(hotkey: toggleHotkey)
                        Button("Clear") {
                            supervisor.send(command: "clearToggleHotkey")
                        }
                    } else {
                        StatusBadge(text: "Inactive", color: AsideDesign.slate)
                    }
                    Button(supervisor.captureTarget == "toggleHotkey" ? "Cancel" : "Set") {
                        if supervisor.captureTarget == "toggleHotkey" {
                            supervisor.send(command: "cancelHotkeyCapture")
                        } else {
                            supervisor.send(command: "startHotkeyCapture", payload: ["target": "toggleHotkey"])
                        }
                    }
                }
            ))
            if let captureTarget = supervisor.captureTarget {
                Text(captureTarget == "hotkey" ? "Press the new push-to-talk shortcut." : "Press the new toggle shortcut.")
                    .font(.caption)
                    .foregroundStyle(AsideDesign.blue)
            }
        }
        .panel()
    }
}

struct PermissionPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Permissions")
                    .font(.headline)
                Spacer()
                Button("Refresh") {
                    supervisor.send(command: "getPermissions")
                }
            }

            PermissionRow(title: "Microphone", subtitle: "Capture your voice for dictation.", key: "microphone", icon: "mic.fill")
            PermissionRow(title: "Accessibility", subtitle: "Insert text wherever the cursor is.", key: "accessibility", icon: "hand.raised.fill")
            PermissionRow(title: "Input Monitoring", subtitle: "Detect configured hotkeys.", key: "inputMonitoring", icon: "keyboard.fill")
        }
        .panel()
    }
}

struct OnboardingPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor
    let onContinue: () -> Void

    private var allGranted: Bool {
        ["microphone", "accessibility", "inputMonitoring"].allSatisfy {
            supervisor.permissions[$0] == "granted"
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(allGranted ? "Permissions are ready" : "Almost there")
                        .font(.headline)
                    Text("Audio stays on this Mac. No cloud. No telemetry. Works offline.")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                StatusBadge(text: allGranted ? "Ready" : "Action needed", color: allGranted ? AsideDesign.green : AsideDesign.amber)
            }

            Text("Continue when Microphone, Accessibility, and Input Monitoring are granted.")
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack {
                Spacer()
                Button("Continue") {
                    onContinue()
                }
                .disabled(!allGranted)
            }
        }
        .panel()
    }
}

struct LocalModelPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    private var modelBinding: Binding<String> {
        Binding(
            get: { supervisor.config.modelSize },
            set: { supervisor.send(command: "setConfig", payload: ["modelSize": $0]) }
        )
    }

    private var languageBinding: Binding<String> {
        Binding(
            get: { supervisor.config.language ?? "" },
            set: { supervisor.send(command: "setConfig", payload: ["language": $0]) }
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Local Model")
                    .font(.headline)
                Spacer()
                StatusBadge(text: supervisor.state == .loading ? "loading" : "ready", color: supervisor.state == .loading ? AsideDesign.blue : AsideDesign.green)
            }
            SettingRow(title: "Model", subtitle: modelLabels[supervisor.config.modelSize] ?? "Local faster-whisper model.", trailing: AnyView(
                Picker("Model", selection: modelBinding) {
                    ForEach(modelOptions, id: \.self) { model in
                        Text(model).tag(model)
                    }
                }
                .labelsHidden()
                .frame(width: 180)
            ))
            SettingRow(title: "Language", subtitle: "Choose a fixed transcription language or auto-detect.", trailing: AnyView(
                Picker("Language", selection: languageBinding) {
                    ForEach(languageOptions, id: \.0) { option in
                        Text(option.0).tag(option.1 ?? "")
                    }
                }
                .labelsHidden()
                .frame(width: 180)
            ))
            PunctuationPanel()
        }
        .panel()
    }
}

struct PunctuationPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    private func send(_ punctuation: PunctuationConfig) {
        supervisor.send(command: "setConfig", payload: ["punctuation": punctuation.payload])
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Punctuation")
                .font(.subheadline.weight(.semibold))
            Picker("Capitalization", selection: Binding(
                get: { supervisor.config.punctuation.capitalization },
                set: {
                    var punctuation = supervisor.config.punctuation
                    punctuation.capitalization = $0
                    send(punctuation)
                }
            )) {
                Text("Sentence").tag("sentence")
                Text("As spoken").tag("as-spoken")
                Text("Off").tag("off")
            }
            .pickerStyle(.segmented)

            Toggle("Smart quotes", isOn: Binding(
                get: { supervisor.config.punctuation.smartQuotes },
                set: {
                    var punctuation = supervisor.config.punctuation
                    punctuation.smartQuotes = $0
                    send(punctuation)
                }
            ))
            Toggle("Space after punctuation", isOn: Binding(
                get: { supervisor.config.punctuation.trailingSpace },
                set: {
                    var punctuation = supervisor.config.punctuation
                    punctuation.trailingSpace = $0
                    send(punctuation)
                }
            ))
        }
        .padding(11)
        .background(AsideDesign.mist.opacity(0.48), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
    }
}

struct DictionaryPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor
    @State private var hotword = ""
    @State private var wrong = ""
    @State private var right = ""

    private var dictionaryFull: Bool {
        supervisor.dictionary.termCount >= supervisor.dictionary.maxTerms
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Dictionary")
                        .font(.headline)
                    Text("\(supervisor.dictionary.termCount) / \(supervisor.dictionary.maxTerms) terms")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button("Edit File") {
                    supervisor.send(command: "openDictionary")
                }
                Button("Reload") {
                    supervisor.send(command: "getDictionary")
                }
            }

            HStack(spacing: 10) {
                DictionaryHint(icon: "sparkles", title: "Hotwords", subtitle: "Names, acronyms, and terms Whisper should expect.")
                DictionaryHint(icon: "arrow.left.arrow.right", title: "Replacements", subtitle: "Consistent fixes after transcription.")
            }

            if supervisor.dictionary.overLimit {
                StatusBadge(text: "Dictionary is over the 50 term limit", color: AsideDesign.red)
            } else if dictionaryFull {
                StatusBadge(text: "Dictionary full", color: AsideDesign.amber)
            }

            HStack {
                EditableField(placeholder: "e.g. HIPAA", text: $hotword)
                    .frame(height: 34)
                Button("Add Hotword") {
                    supervisor.send(command: "addHotword", payload: ["term": hotword])
                    hotword = ""
                }
                .disabled(dictionaryFull || hotword.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }

            HStack {
                EditableField(placeholder: "wrong", text: $wrong)
                    .frame(height: 34)
                Text("→")
                    .foregroundStyle(.secondary)
                EditableField(placeholder: "right", text: $right)
                    .frame(height: 34)
                Button("Add Replacement") {
                    supervisor.send(command: "addReplacement", payload: ["wrong": wrong, "right": right])
                    wrong = ""
                    right = ""
                }
                .disabled(dictionaryFull || wrong.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || right.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Hotwords")
                    .font(.subheadline.weight(.semibold))
                if supervisor.dictionary.hotwords.isEmpty {
                    EmptyState(text: "No hotwords yet.")
                }
                FlowLayout(spacing: 8) {
                    ForEach(supervisor.dictionary.hotwords, id: \.self) { term in
                        RemovableTag(text: term) {
                            supervisor.send(command: "removeHotword", payload: ["term": term])
                        }
                    }
                }
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Replacements")
                    .font(.subheadline.weight(.semibold))
                if supervisor.dictionary.replacements.isEmpty {
                    EmptyState(text: "No replacements yet.")
                }
                VStack(spacing: 6) {
                    ForEach(supervisor.dictionary.replacements, id: \.self) { rule in
                        HStack {
                            Text(rule.wrong)
                            Text("→").foregroundStyle(.secondary)
                            Text(rule.right)
                            Spacer()
                            Button {
                                supervisor.send(command: "removeReplacement", payload: ["wrong": rule.wrong])
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.secondary)
                        }
                        .font(.caption)
                        .padding(8)
                        .background(AsideDesign.mist.opacity(0.48), in: RoundedRectangle(cornerRadius: 6, style: .continuous))
                    }
                }
            }
        }
        .panel()
    }
}

struct DictionaryHint: View {
    let icon: String
    let title: String
    let subtitle: String

    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            Image(systemName: icon)
                .foregroundStyle(AsideDesign.blue)
                .frame(width: 18)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption.weight(.semibold))
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(AsideDesign.mist.opacity(0.48), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
    }
}

struct EmptyState: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(AsideDesign.mist.opacity(0.30), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
    }
}

struct EditableField: NSViewRepresentable {
    let placeholder: String
    @Binding var text: String

    func makeNSView(context: Context) -> NSTextField {
        let field = NSTextField()
        field.placeholderString = placeholder
        field.isBordered = true
        field.isBezeled = true
        field.bezelStyle = .roundedBezel
        field.drawsBackground = true
        field.backgroundColor = .textBackgroundColor
        field.delegate = context.coordinator
        field.font = .systemFont(ofSize: 14)
        field.focusRingType = .default
        return field
    }

    func updateNSView(_ field: NSTextField, context: Context) {
        if field.stringValue != text {
            field.stringValue = text
        }
        field.placeholderString = placeholder
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(text: $text)
    }

    final class Coordinator: NSObject, NSTextFieldDelegate {
        @Binding var text: String

        init(text: Binding<String>) {
            _text = text
        }

        func controlTextDidChange(_ notification: Notification) {
            guard let field = notification.object as? NSTextField else {
                return
            }
            text = field.stringValue
        }
    }
}

struct VoiceCommandsPanel: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Voice Commands")
                .font(.headline)
            VoiceCommandGroup(title: "Punctuation", commands: [
                ("Period", "period / full stop", "Insert ."),
                ("Comma", "comma", "Insert ,"),
                ("Question Mark", "question mark", "Insert ?"),
                ("Exclamation", "exclamation point / exclamation mark", "Insert !"),
                ("New Line", "new line / newline", "Insert one line break"),
                ("New Paragraph", "new paragraph", "Insert two line breaks"),
            ])
            VoiceCommandGroup(title: "Actions", commands: [
                ("Delete That", "delete that", "Remove the last dictation"),
                ("Undo", "undo", "Send Cmd-Z"),
                ("Select All", "select all", "Send Cmd-A"),
                ("Copy", "copy that / copy all", "Send Cmd-C"),
            ])
            VoiceCommandGroup(title: "Modes", commands: [
                ("Numbers Mode", "numbers mode", "Convert spoken numbers to digits"),
                ("Words Mode", "words mode", "Return to normal dictation"),
            ])
        }
        .panel()
    }
}

struct VoiceCommandGroup: View {
    let title: String
    let commands: [(String, String, String)]

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            Text(title)
                .font(.subheadline.weight(.semibold))
            ForEach(commands, id: \.0) { command in
                VoiceCommandRow(command: command.0, spoken: command.1, behavior: command.2)
            }
        }
    }
}

struct AdvancedPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Advanced")
                .font(.headline)
            SettingRow(title: "Helper", subtitle: "Restart the Python helper if the model or hotkey state gets stuck.", trailing: AnyView(
                Button("Restart Helper") {
                    supervisor.restartHelper()
                }
            ))
            SettingRow(title: "Config", subtitle: "Reload settings from ~/.aside/config.json.", trailing: AnyView(
                Button("Reload Config") {
                    supervisor.send(command: "reloadConfig")
                }
            ))
            Text("No network calls. No cloud language. No telemetry.")
                .font(.callout)
                .foregroundStyle(.secondary)
        }
        .panel()
    }
}

struct AboutPanel: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("About Aside")
                .font(.headline)
            HStack(spacing: 14) {
                AppLogoView()
                    .frame(width: 58, height: 58)
                VStack(alignment: .leading, spacing: 4) {
                    Text("Private voice dictation for Mac")
                        .font(.subheadline.weight(.semibold))
                    Text("Local faster-whisper transcription with push-to-talk and toggle hotkeys.")
                        .foregroundStyle(.secondary)
                }
            }
            VStack(alignment: .leading, spacing: 8) {
                AboutRow(label: "Privacy", value: "Audio stays on this Mac. No cloud. No telemetry.")
                AboutRow(label: "Engine", value: "Python helper, faster-whisper, Quartz text injection.")
                AboutRow(label: "UI", value: "Native SwiftUI shell migration.")
                AboutRow(label: "License", value: "Apache 2.0")
            }
        }
        .panel()
    }
}

struct AboutRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label)
                .font(.caption.weight(.semibold))
                .foregroundStyle(AsideDesign.slate)
                .frame(width: 70, alignment: .leading)
            Text(value)
                .font(.caption)
                .foregroundStyle(.secondary)
            Spacer()
        }
    }
}

struct PermissionRow: View {
    @EnvironmentObject private var supervisor: HelperSupervisor
    let title: String
    let subtitle: String
    let key: String
    let icon: String

    private var value: String {
        supervisor.permissions[key] ?? "unknown"
    }

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(value == "granted" ? AsideDesign.green : AsideDesign.blue)
                .frame(width: 30)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.subheadline.weight(.semibold))
                Text(subtitle).font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            StatusBadge(text: value, color: value == "granted" ? AsideDesign.green : AsideDesign.amber)
            Button("Open Settings") {
                supervisor.send(command: "requestPermission", payload: ["permission": key])
            }
        }
        .padding(10)
        .background(AsideDesign.mist.opacity(0.55), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}

struct SettingRow: View {
    let title: String
    let subtitle: String
    let trailing: AnyView

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            trailing
        }
        .padding(11)
        .background(AsideDesign.mist.opacity(0.48), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
    }
}

struct KeycapRow: View {
    let hotkey: HotkeyConfig?

    var body: some View {
        HStack(spacing: 5) {
            if let hotkey {
                ForEach(hotkey.displayParts, id: \.self) { part in
                    Text(part)
                        .font(.system(size: 13, weight: .semibold))
                        .padding(.horizontal, 9)
                        .padding(.vertical, 6)
                        .background(Color.white.opacity(0.82), in: RoundedRectangle(cornerRadius: 6, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 6, style: .continuous)
                                .stroke(Color.black.opacity(0.12))
                        )
                }
            } else {
                StatusBadge(text: "Inactive", color: AsideDesign.slate)
            }
        }
    }
}

struct TagCloud: View {
    let tags: [String]

    var body: some View {
        FlowLayout(spacing: 8) {
            ForEach(tags, id: \.self) { tag in
                Text(tag)
                    .font(.caption.weight(.semibold))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(AsideDesign.mist, in: Capsule())
            }
        }
    }
}

struct RemovableTag: View {
    let text: String
    let onRemove: () -> Void

    var body: some View {
        HStack(spacing: 6) {
            Text(text)
            Button {
                onRemove()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 9, weight: .bold))
            }
            .buttonStyle(.plain)
        }
        .font(.caption.weight(.semibold))
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(AsideDesign.mist, in: Capsule())
    }
}

struct VoiceCommandRow: View {
    let command: String
    let spoken: String
    let behavior: String

    var body: some View {
        HStack {
            Image(systemName: "text.badge.checkmark")
                .foregroundStyle(AsideDesign.slate)
            VStack(alignment: .leading, spacing: 2) {
                Text(command)
                    .font(.subheadline.weight(.semibold))
                Text(spoken)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Text(behavior)
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(width: 170, alignment: .leading)
        }
        .padding(11)
        .background(AsideDesign.mist.opacity(0.48), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
    }
}

struct TutorialPanel: View {
    @State private var scratchText = ""

    private let prompts = [
        ("Basic dictation", "hello world period"),
        ("Line breaks", "first line new line second line"),
        ("Actions", "delete that"),
        ("Numbers", "numbers mode one two three words mode"),
        ("Boundary check", "I will delete that section later"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Practice")
                .font(.headline)
            Text("Use these prompts in any text field to check hotkeys, punctuation, actions, and boundaries.")
                .font(.callout)
                .foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Scratch Pad")
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    Button("Clear") {
                        scratchText = ""
                    }
                    .disabled(scratchText.isEmpty)
                }
                TextEditor(text: $scratchText)
                    .font(.system(size: 14))
                    .scrollContentBackground(.hidden)
                    .padding(8)
                    .frame(minHeight: 145)
                    .background(Color.white.opacity(0.82), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous)
                            .stroke(Color.black.opacity(0.08))
                    )
            }
            ForEach(prompts, id: \.0) { prompt in
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "target")
                        .foregroundStyle(AsideDesign.blue)
                        .frame(width: 24)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(prompt.0)
                            .font(.subheadline.weight(.semibold))
                        Text(prompt.1)
                            .font(.system(size: 13, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(11)
                .background(AsideDesign.mist.opacity(0.48), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
            }
        }
        .panel()
    }
}

struct ControlsPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recording Controls")
                .font(.headline)

            HStack {
                Button {
                    supervisor.send(command: "startRecording")
                } label: {
                    Label("Start Recording", systemImage: "mic.fill")
                }
                .disabled(supervisor.state != .ready)

                Button {
                    supervisor.send(command: "stopRecording")
                } label: {
                    Label("Stop and Transcribe", systemImage: "stop.fill")
                }
                .disabled(supervisor.state != .recording)

                Spacer()

                Button {
                    supervisor.restartHelper()
                } label: {
                    Label("Restart Helper", systemImage: "arrow.clockwise")
                }
            }

            Text("The configured push-to-talk and toggle hotkeys are still handled by the Python helper.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .panel()
    }
}

struct LogPanel: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Helper Events")
                .font(.headline)

            VStack(alignment: .leading, spacing: 6) {
                ForEach(supervisor.eventLog.suffix(8), id: \.self) { line in
                    Text(line)
                        .font(.system(size: 11, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .padding(10)
            .frame(minHeight: 90, alignment: .topLeading)
            .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .panel()
    }
}

struct MenuBarContent: View {
    @EnvironmentObject private var supervisor: HelperSupervisor

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Aside")
                    .font(.headline)
                Spacer()
                StatusBadge(text: supervisor.state.title, color: supervisor.state.color)
            }

            VStack(spacing: 8) {
                ZStack {
                    Circle()
                        .stroke(supervisor.state.color.opacity(0.25), lineWidth: 2)
                        .frame(width: 88, height: 88)
                    Image(systemName: supervisor.state.systemImage)
                        .font(.system(size: 30, weight: .semibold))
                        .foregroundStyle(supervisor.state.color)
                }
                Text(supervisor.state == .recording ? "Hold to speak" : supervisor.state == .transcribing ? "This won't take long" : "Ready when you are")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity)

            VStack(alignment: .leading, spacing: 5) {
                Label("Audio stays on this Mac", systemImage: "checkmark.circle.fill")
                    .foregroundStyle(AsideDesign.green)
                Text("No cloud. No telemetry.")
                    .foregroundStyle(.secondary)
            }
            .font(.caption)

            Divider()
            Button("Start Recording") {
                supervisor.send(command: "startRecording")
            }
            .disabled(supervisor.state != .ready)
            Button("Stop and Transcribe") {
                supervisor.send(command: "stopRecording")
            }
            .disabled(supervisor.state != .recording)
            Button("Restart Helper") {
                supervisor.restartHelper()
            }
            Divider()
            Button("Settings...") {
                NSApplication.shared.activate(ignoringOtherApps: true)
            }
            Button("Permissions...") {
                supervisor.send(command: "getPermissions")
                NSApplication.shared.activate(ignoringOtherApps: true)
            }
            Divider()
            Button("Quit Aside") {
                supervisor.shutdownHelper()
                NSApplication.shared.terminate(nil)
            }
        }
        .padding(10)
        .frame(width: 260)
    }
}

struct StatusBadge: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .foregroundStyle(color)
            .background(color.opacity(0.13), in: Capsule())
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? 420
        var currentX: CGFloat = 0
        var currentY: CGFloat = 0
        var lineHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if currentX > 0 && currentX + size.width > maxWidth {
                currentX = 0
                currentY += lineHeight + spacing
                lineHeight = 0
            }
            currentX += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }

        return CGSize(width: maxWidth, height: currentY + lineHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var currentX = bounds.minX
        var currentY = bounds.minY
        var lineHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if currentX > bounds.minX && currentX + size.width > bounds.maxX {
                currentX = bounds.minX
                currentY += lineHeight + spacing
                lineHeight = 0
            }
            subview.place(at: CGPoint(x: currentX, y: currentY), proposal: ProposedViewSize(size))
            currentX += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }
    }
}

extension View {
    func panel() -> some View {
        self
            .padding(16)
            .background(Color.white.opacity(0.72), in: RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: AsideDesign.radius, style: .continuous)
                    .stroke(Color.black.opacity(0.08))
            )
    }

    func sidebarRow(selected: Bool = false) -> some View {
        self
            .font(.system(size: 14, weight: selected ? .semibold : .regular))
            .foregroundStyle(selected ? Color.white : Color.primary)
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(selected ? AsideDesign.blue : Color.clear, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}
