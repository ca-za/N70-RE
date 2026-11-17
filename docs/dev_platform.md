# Development platform & earbud architecture

Everything we learned about **how the N70 is built** (the WuQi SDK, toolchain, packaging, flashing) and **how the earbud is put together** (chip, cores, memory, DSP, debug, case). This is a consolidation; the detail pages are [firmware.md](firmware.md), [firmware_internals.md](firmware_internals.md), [hardware.md](hardware.md), [factory_cli.md](factory_cli.md) and [sources.md](sources.md). Marked ✅ verified on device / from the decompressed firmware, otherwise source-only.

## 1. The development platform (WuQi ADK)

The N70 is built on **WuQi's audio ADK**, the vendor SDK for the WQ703X family. Everything below the QCY application layer (`qcy_app`) is WuQi's: Bluetooth stack, DSP libraries, OTA, factory CLI, drivers, RTOS.

### Which SDK / version ✅

From the decompressed firmware build tag and project path:

| | |
|---|---|
| Build tag | `QCY_HT18-7035AX-B-ADK_1.3.6.27-LDAC-20251219` ✅ |
| Firmware string | `FW-VERSION-v0.3.0.13` ✅ |
| ADK version | **`wq-adk` 1.3.6.27**, built 2025-12-19 |
| Project path (left in the binary) | `/root/projects/HT18/wq-adk/` ✅ |
| RTOS | FreeRTOS (SDK dir `os/FreeRTOS`, source-only via CSDN) |

There are **two ADK generations** and it matters which one you look at:

| Generation | Version seen | Source layout | Where |
|---|---|---|---|
| Older | `sdk_tws_6.1.0.295` | `core0/src/{app,lib,driver,os}`, SCons build | public mirror [qqq5127/ZT210](https://github.com/qqq5127/ZT210) |
| Newer (**the N70's**) | `wq-adk 1.3.6.27` | `components/` + `wqcore` | **NDA-only, not public** |

The older tree is a faithful structural reference (same OTA format, same charger-box code, same CLI/GTP transport — that is how we cracked the firmware format), but it is **not** the N70's code. The N70's exact `wq-adk 1.3.6.27` / `wq-audio` package is delivered to device makers under NDA and was **not found anywhere public** (GitHub, Bing, Baidu, Gitee all searched; exact package names `wq-audio_1.4.0.69`, `wq-adk_1.3.6` return zero hits).

### Toolchain (gated)

Building for this chip needs three per-core toolchains plus the NPU compiler — all gated behind WuQi's licensed download server:

| Target | Toolchain | Note |
|---|---|---|
| BT core + app core (RISC-V) | `riscv*-elf-gcc` (GCC ~14.2) | RV32IMAFC |
| DSP (Xtensa HiFi 5) | `xtensa-wuqi-elf-gcc 12.2` **and** Cadence `xt-clang` RI-2020.4 | Cadence license required |
| NPU | NeuroWeave / XNNC | WuQi's NN compiler |

(Toolchain names are source-only, from the `silero-vad-test` reference repo and CSDN; versions are consistent with the firmware's compiler strings.)

### Build → package → flash pipeline

```
ADK source ──(per-core toolchains)──► ELF per core
     │
     ▼
.wpk  = plain ZIP   (contains app_evt.xml, audmap_config.json, the per-core images)
     │
     ▼  WuQi UI / packaging tool  (selects image regions, LZMA-compresses)
OTA .bin  = ota_file_header_t + pack_desc_t(magic 0xABCD6543) + image_desc[] + CRC32
            + LZMA blocks + CRC32          ◄── this is what we downloaded & unpacked ✅
     │
     ▼  production flasher  Wuqi.Beetle.Burn.exe
single-wire UART burn (BOOT→VDD), "POGO-pin single-line upgrade"  → chip flash
```

- The `.wpk` is just a ZIP (`core0/tools/SCons/firmware_package.py` in ZT210). ✅ for the format.
- The OTA `.bin` layout, the LZMA (not encryption), and both CRC-32s are **confirmed by parsing our image** — see [firmware.md](firmware.md). The compression happens in the packaging tool, not a cipher.
- Factory flashing is **single-wire UART** over the test pads / POGO pins (`Wuqi.Beetle.Burn.exe`, BOOT pulled to VDD). Source-only (CSDN), consistent with the UART debug path below.

### Reference material (assumes you already have the ADK)

- [qqq5127/ZT210](https://github.com/qqq5127/ZT210) — full older-gen source (OTA, charger-box, CLI/GTP). Our primary structural reference.
- [haikow/silero-vad-test](https://github.com/haikow/silero-vad-test) — build flow + toolchain list + patches against `wq-adk 1.4.0.69` for a 7036.
- [TommyLITommy/WUQI_SDK_Learning_And_Recording](https://github.com/TommyLITommy/WUQI_SDK_Learning_And_Recording) — deep wq-adk internals, incl. the POGO-pin single-line flashing flow.
- CSDN articles on `wq_sdk_env` (Windows build env), OTA, app comms, single-wire burn — see [sources.md](sources.md).

### Can we build our own firmware?

**No, not realistically.** Gated on three things we don't have and can't get without being a WuQi customer: the **NDA ADK package** (`wq-adk 1.3.6.27`), the **licensed toolchain** (esp. the Cadence Xtensa license), and the **N70 board config** — plus physical test-pad flashing with a bricking risk. See [ideas.md](ideas.md). The reachable, valuable target (the A001 control protocol) is already fully mapped.

## 2. Aufbau der Kopfhörer (earbud architecture)

### Chip: WuQi WQ703X (7035AX / code prints WQ7036) ✅

A single SoC per earbud carrying **three CPU cores + DSP + NPU**, hybrid ANC, dual-mode Bluetooth. Confirmed from the firmware; the `7033` we originally guessed is only the GATT service UUID / SDK family name, not the die. Datasheet facts (dual RISC-V, HiFi 5 DSP, NPU, hybrid ANC, BLE Audio capable) apply to the 703X series. Full chip discussion in [hardware.md](hardware.md).

### The three cores + DSP ✅

From the unpacked OTA image, each code image starts with a 32-byte `iot_flash_image_header_t` (guard `0xA4E49A17`); code runs at the header's `start` address. Cores identified by run address + architecture:

| Core | Arch | Run address | Flash LMA | Role |
|---|---|---|---|---|
| **BT core** | RISC-V RV32IMAFC | `0xB4010020` | `0x010000` | BT controller + host: A2DP / AVRCP / HFP, RPC |
| **DSP** | Xtensa Cadence **HiFi 5** | `0x26008000` | `0x0AB000` | audio DSP: AEC/DRC/EQ/ES/volume, LDAC decode, ANC |
| **App core** | RISC-V RV32IMAFC | `0x34169020` | `0x169000` | `qcy_app` — the A001 protocol logic, user commands |

Plus two data images: config (`0x3EE000`) and tone/voice prompts (`0x3F0000`). This matches the datasheet's "2× RISC-V + HiFi 5 DSP". Global data / `_gp` sits in the `0x02xxxxxx` region, copied from flash at boot. Memory map and how to load each image in radare2/Ghidra: [firmware_internals.md](firmware_internals.md).

### What each part actually does ✅

- **BT core** — classic Bluetooth only (A2DP/AVRCP/HFP). LE Audio is **compiled-but-absent**: two orphan file strings, but **no LC3 codec, no isochronous (CIS/BIS) path, no LE Audio GATT profiles** → LE Audio cannot be enabled by a flag. See [firmware_internals.md](firmware_internals.md).
- **DSP (HiFi 5)** — all the audio compute: ANC (hybrid feedforward+feedback), call noise reduction (the "3-mic AI ENC": `wq aec` / `wq es` / `wq med`), EQ, and **LDAC decode**. The chip's NPU/AI budget goes here, **not** to keyword spotting.
- **App core** — runs `qcy_app`: handles the A001 command frames, builds the BLE advertisement, forwards battery, talks to the case.
- **No on-device keyword spotting / wake word.** The NPU is present but no KWS/hotword/VAD/ASR model ships; "voice assistant" is tap-to-invoke the phone's Siri/Google over HFP (`+VR`, `+APLSIRI`). ✅

### Debug & logging interface — UART, not USB ✅

Where the earbud's own diagnostics come out:

- **Logs and core dumps go over UART.** Firmware strings: `"[auto]Core dump has written to uart."`, `pl_uart1.c`, `wq_uart.c`, and SDK symbols `DBGLOG_DUMP_UART`, `GENERIC_TRANSMISSION_IO_UART`. The `COM6/COM7/COM8/COM9` strings are the host-tool (Windows) side of that UART. So the realistic way to read `dbglog` / core dumps is the earbud's **UART test pads** (the same single-wire/UART interface used for factory flashing).
- **No USB on the audio chip.** The ADK has **no USB driver** (no `usb`/`usb_cdc`/`usb_device` files or strings), so the WQ703X almost certainly has no USB device mode. You cannot get earbud logs "over USB" from the chip.
- **Factory CLI** (67 commands) rides the same UART via the GTP transport. It is also wired to GATT service 7033 (1001/1002) but **not serviced over BLE** in shipping firmware. Documentation only; 7033 is write-forbidden. See [factory_cli.md](factory_cli.md).

### Charging case — separate MCU, no radio ✅ / source

- The case has **its own controller/MCU on a separate chip** with **its own firmware** (not part of the earbud OTA image we unpacked).
- **No Bluetooth.** It talks to the buds over the **charging contacts (pogo pins)** with a bit-banged single-wire protocol modulated onto the charge line (8-bit opcodes: lid open/close, button long-press, enter pairing / DUT / OTA, shutdown, case battery). Source: ZT210 `vendor/charger_box/charger_box_wq.c`.
- The case **USB-C is for charging** (VBUS into the case charger IC). Its data lines are most likely unconnected or charger-negotiation only — getting earbud debug logs through the case USB is **unlikely** (and we don't have the case hardware/firmware to confirm). Full detail: [hardware.md](hardware.md) "Charging case".

## 3. One-line summary

The N70 is a **WuQi WQ703X** running firmware built with **WuQi `wq-adk` 1.3.6.27** (FreeRTOS, three cores: two RISC-V + one Xtensa HiFi 5 DSP), packaged into an LZMA-compressed OTA `.bin` and flashed single-wire over UART/pogo pins. The QCY layer on top is just `qcy_app` on the app core. The SDK and toolchain are NDA/licensed and not public; the firmware itself is fully readable (unpacked, not encrypted), and the BLE control protocol is fully mapped and device-verified. The case is a dumb-radio, smart-MCU unit talking to the buds over the charge line.
