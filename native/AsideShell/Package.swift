// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "AsideShell",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "AsideShell", targets: ["AsideShell"])
    ],
    targets: [
        .executableTarget(
            name: "AsideShell",
            path: "Sources/AsideShell"
        ),
        .testTarget(
            name: "AsideShellTests",
            dependencies: ["AsideShell"],
            path: "Tests/AsideShellTests"
        )
    ]
)
