import Cocoa

final class DeckApp: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    var child: Process?
    var outputPipe: Pipe?
    var outputBuffer = ""
    let status = NSTextField(wrappingLabelWithString: "Starting your desk…")
    let startButton = NSButton(title: "Start & Cast", target: nil, action: nil)
    let stopButton = NSButton(title: "Stop", target: nil, action: nil)
    let info = Bundle.main.infoDictionary ?? [:]

    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 440, height: 280),
                          styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Desk Deck"
        window.isReleasedWhenClosed = false
        let title = NSTextField(labelWithString: "Your desk, one tap away.")
        title.font = .systemFont(ofSize: 25, weight: .semibold)
        let subtitle = NSTextField(wrappingLabelWithString: "Open this app to start your local server and cast to your Nest Hub.")
        subtitle.textColor = .secondaryLabelColor
        subtitle.font = .systemFont(ofSize: 15)
        status.font = .systemFont(ofSize: 14, weight: .medium)
        status.maximumNumberOfLines = 4
        startButton.target = self; startButton.action = #selector(start)
        stopButton.target = self; stopButton.action = #selector(stop)
        let settings = NSButton(title: "Configuration…", target: self, action: #selector(openConfig))
        let controls = NSStackView(views: [startButton, stopButton, settings])
        controls.spacing = 10
        let stack = NSStackView(views: [title, subtitle, status, controls])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 20
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 26),
            stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -26),
            stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 26)
        ])
        window.center(); window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        start()
    }

    @objc func start() {
        guard child == nil else { return }
        guard let python = info["DeskDeckPython"] as? String,
              let config = info["DeskDeckConfig"] as? String,
              let root = info["DeskDeckRoot"] as? String else {
            status.stringValue = "Rebuild this app using the Desk Deck setup guide."
            return
        }
        guard FileManager.default.fileExists(atPath: config) else {
            status.stringValue = "Setup needed: create your private configuration using the README, then start again."
            return
        }
        let process = Process(); let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = ["-u", "-m", "deskdeck", "desktop", "--config", config]
        process.currentDirectoryURL = URL(fileURLWithPath: root)
        process.standardOutput = pipe; process.standardError = pipe
        outputBuffer = ""; child = process; outputPipe = pipe
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            DispatchQueue.main.async {
                guard let self = self, self.child === process else { return }
                self.outputBuffer += text
                while let end = self.outputBuffer.firstIndex(of: "\n") {
                    let line = String(self.outputBuffer[..<end])
                    self.outputBuffer.removeSubrange(...end)
                    if line.hasPrefix("Page received:") {
                        self.status.stringValue = "Connected to your Nest Hub. Your touch deck is ready."
                    } else if line.hasPrefix("Error:") || line.hasPrefix("No page receipt") || line.hasPrefix("Local server ready") {
                        self.status.stringValue = line
                    }
                }
                if self.outputBuffer.count > 8192 { self.outputBuffer = "" }
            }
        }
        process.terminationHandler = { [weak self] stopped in
            DispatchQueue.main.async {
                guard let self = self, self.child === stopped else { return }
                self.outputPipe?.fileHandleForReading.readabilityHandler = nil
                self.child = nil; self.outputPipe = nil
                self.startButton.isEnabled = true; self.stopButton.isEnabled = false
                if stopped.terminationStatus != 0 {
                    self.status.stringValue = "Couldn’t start or cast. Check configuration, network, and whether another server is using the port."
                }
            }
        }
        do {
            try process.run()
            startButton.isEnabled = false; stopButton.isEnabled = true
            status.stringValue = "Starting your local server and connecting to your Nest Hub…"
        } catch {
            child = nil; outputPipe = nil
            status.stringValue = "Python could not start. Rebuild this app after setting up Desk Deck."
        }
    }

    @objc func stop() {
        if let running = child, running.isRunning { running.terminate(); running.waitUntilExit() }
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        child = nil; outputPipe = nil
        startButton.isEnabled = true; stopButton.isEnabled = false
        status.stringValue = "Stopped. Start again whenever you’re ready."
    }
    @objc func openConfig() {
        if let path = info["DeskDeckConfig"] as? String {
            NSWorkspace.shared.selectFile(path, inFileViewerRootedAtPath: "")
        }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil); return true
    }
    func applicationWillTerminate(_ notification: Notification) { stop() }
}
let application = NSApplication.shared
let delegate = DeckApp()
application.delegate = delegate
let menu = NSMenu()
let appItem = NSMenuItem()
let appMenu = NSMenu()
appMenu.addItem(withTitle: "Quit Desk Deck", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
appItem.submenu = appMenu; menu.addItem(appItem); application.mainMenu = menu
application.setActivationPolicy(.regular)
application.run()
