# N70-RE

Reverse engineering of the **QCY MeloBuds N70** (true wireless earbuds with ANC, LDAC, multipoint).
Knowledge collected while building a macOS integration that controls the earbuds over Bluetooth LE.

## Status in one sentence

The earbuds can be fully remote-controlled from a Mac over Bluetooth LE (noise control, EQ, game mode, prompt volume, live battery). The protocol is known and tested on this device. The official QCY app (4.0.7) has been decompiled: the full A001 command set and the OTA mechanism (Wuqi service 7033) are documented from its code, and the firmware image (HT18, 3.0.13) has been archived. What's still missing: the firmware is encrypted, so the chip's code and keys remain out of reach.

## Contents

| File | Contents |
|---|---|
| [docs/hardware.md](docs/hardware.md) | Device, chip (Wuqi WQ7033), addresses, Bluetooth profiles |
| [docs/gatt.md](docs/gatt.md) | BLE services and characteristics (A001, 7033, 180A, FE2C) |
| [docs/protocol.md](docs/protocol.md) | QCY protocol: frame format, all known commands, **verified on the device** vs. source only |
| [docs/advertising.md](docs/advertising.md) | BLE advertisements: battery L/R/case, addresses, when they are sent |
| [docs/eq.md](docs/eq.md) | Parametric EQ: format, factory curve, presets, tested writes |
| [docs/controlpanel.md](docs/controlpanel.md) | The N70's own server feature list: which opcodes it supports, ANC values, key remap |
| [docs/firmware.md](docs/firmware.md) | Firmware image: how to fetch the URL (guest token), the encrypted .bin, header |
| [docs/ota.md](docs/ota.md) | OTA over Wuqi service 7033: framing, state machine, the read-only device-info query |
| [docs/sources.md](docs/sources.md) | Sources, contradictions between sources |
| [docs/ideas.md](docs/ideas.md) | Open questions, next steps, risks |
| `data/` | Raw data: factory EQ, settings blobs, advertisements, N70 control-panel JSON |
| `tools/` | Swift test programs (CoreBluetooth) |

## Building the tools

```sh
cd tools
swiftc -O adv_scan.swift -o adv_scan -Xlinker -sectcreate -Xlinker __TEXT -Xlinker __info_plist -Xlinker Info.plist
```

The embedded `Info.plist` makes macOS ask for the Bluetooth permission.

| Tool | Purpose |
|---|---|
| `adv_scan.swift` | capture all BLE advertisements for 12 s (name, manufacturer data, service data) |
| `gatt_services.swift` | look for LE Audio services, list all services of the N70 |
| `gatt_dump.swift` | read services + characteristics + descriptors (originally written for a ZMK keyboard battery, adjust the filter) |
| `device_info.swift` | read the Device Information Service (180A) |
| `list_7033.swift` | list the characteristics of service 7033 (reads/writes nothing) |

A full controller (keeping the connection, sending commands, tracking state) follows the protocol in [docs/protocol.md](docs/protocol.md); see [docs/hardware.md](docs/hardware.md) for connection behavior.

## Rules

- Do not send unknown commands to the earbuds. New commands only if they come from a source, and always read back.
- **Never write to service 7033** (probably the firmware update channel, risk of bricking).
- Save the original state before write tests (e.g. `data/eq_original.hex`).
