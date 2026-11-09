# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Reverse engineering notes for the QCY MeloBuds N70 earbuds (chip very likely Wuqi WQ7033), controlled from macOS over BLE. This is a documentation repo with a few small Swift/CoreBluetooth probe tools; there is no app, no test suite, no linter.

## Rules

- **The repo is English-only** (docs, comments, commit messages, tool output). Talk to the user in German, plain language.
- The current knowledge is in `README.md` and `docs/`. Add new findings there and clearly mark verified on device ✅ vs. source only. Also note which source a claim comes from (`docs/sources.md` lists them and their contradictions).
- **Commit and push after every change** (`main`, remote `https://github.com/ca-za/N70-RE`, public).
- No unknown commands to the earbuds. Only commands from a source; save the original state first (e.g. `data/eq_original.hex`), read back afterwards and restore.
- **Never write to service 7033** (probably the firmware update channel, risk of bricking). `tools/list_7033.swift` only lists its characteristics.
- Another app on this Mac may already hold a BLE connection to the earbuds; do not disconnect or interfere with it.
- Downloaded files (APK, firmware) go into their own empty folder under `work/` (gitignored, not in the repo), never execute them; run Python on them with `-I`.

## Building and running the tools

Each file in `tools/` is a standalone script, compiled on its own. The `Info.plist` must be embedded, otherwise macOS never asks for the Bluetooth permission:

```sh
cd tools
swiftc -O adv_scan.swift -o adv_scan -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker Info.plist
./adv_scan
```

Compiled binaries are gitignored (`tools/*` except `*.swift` and `Info.plist`).

How the tools reach the device: they do not scan and connect from scratch. They call `retrieveConnectedPeripherals(withServices: [A001])`, i.e. they reuse the BLE link that macOS already holds (CoreBluetooth shares connections system-wide), then `connect` and discover one service. If no link exists, the buds must be advertising (open the case / take them out) – see `docs/hardware.md`. Each tool exits on a timeout.

Note: `tools/gatt_dump.swift` is currently an Objective-C runtime class inspector (prints methods/ivars of class names given as arguments), not the GATT dumper the README describes.

## Protocol essentials (details in `docs/protocol.md`)

- Control service `A001`: write commands (without response) to `1001`, replies arrive as notifications on `1002`. Enable notify **before** the first request or the reply is lost.
- Frame: `FF <len> <op> <plen> <params...>`, `len = plen + 2`, no checksum. Query a value with `FF 03 FE 01 <op>`. One reply frame can hold several `<op> <plen> <params>` blocks.
- A plain **read** of `1002` returns all settings in one blob (examples in `data/settings_blobs.txt`).
- Battery comes from BLE advertisements (`docs/advertising.md`, raw samples in `data/adverts.txt`); the EQ format is in `docs/eq.md`.
- Firmware and OTA: `docs/firmware.md` (the encrypted .bin, how its URL is fetched via a QCY guest token) and `docs/ota.md` (the Wuqi service 7033 protocol). The N70's QCY-internal model is **HT18**, modelId/vendor ID `0x5D45` = 23877.
- The official QCY app (`com.qcymall.googleearphonesetup`) decompiles to `work/qcy-app-4.0.7-jadx/` (jadx, gitignored). It has no N70-specific code; features come from a server-downloaded control-panel JSON. `docs/protocol.md` has the full opcode table from it (source only vs. ✅ device-verified).
- The N70's own feature/command list is `data/controlpanel_n70.json` (`docs/controlpanel.md`), fetched from `api.watch.qcy.com/product/findControlPanels` (modelId 23877). Its `cmdid` fields are decimal A001 opcodes and confirm which commands the N70 supports.
- Open questions and planned next steps live in `docs/ideas.md`.
