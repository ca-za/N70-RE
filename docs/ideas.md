# Open questions and next steps

## Done (2026-11-09/10)

1. **QCY app decompiled** (jadx, `work/qcy-app-4.0.7-jadx/`): full opcode table → [protocol.md](protocol.md); OTA over service 7033 → [ota.md](ota.md); firmware is downloaded from a server, not in the APK → [firmware.md](firmware.md).
2. **Firmware obtained and unpacked**: HT18 3.0.13, LZMA-compressed (not encrypted) → [firmware.md](firmware.md). Internal model HT18 confirmed.
3. **N70 server control panel** fetched → [controlpanel.md](controlpanel.md): confirms which opcodes the N70 supports, ANC values, EQ presets. Resolved `0x19` (prompt language), `0x1F` (auto power-off), `0x04` (play state), and that `0x2A` (wind) is live.

## Firmware – SOLVED (2026-11-10): not encrypted, just LZMA-compressed

The OTA `.bin` is **not encrypted**. The 8.0 entropy was LZMA compression. A public GitHub mirror of the WuQi SDK ([qqq5127/ZT210](https://github.com/qqq5127/ZT210), same ADK family) gave the device-side OTA source (`ota.h`, `ota.c`, `app_wqota.c`), which showed the exact package format and that the receive path does only magic + CRC-32 checks and LZMA decompression — no cipher, no key. We parsed our N70 image: both CRC-32s match and all six blocks decompress to the stated sizes. Format, layout and extractor are in [firmware.md](firmware.md) / [`tools/ota_unpack.py`](../tools/ota_unpack.py).

Result: full decompressed firmware for all cores (core0/core1/DSP/tone), readable RISC-V. Chip identity corrected to **WQ703X (7035AX/7036)**.

### Next (optional)
- Disassemble the RISC-V images in Ghidra/radare2 at their known load addresses (core0 0x10000, core1 0xAB000, DSP 0x169000).
- The search sweep for a key/decryptor turned out moot; it was never encrypted. (No WQ7033 presence on 4PDA/RuTracker; the readable SDK came from GitHub, not the NDA leaks.)

**Conclusion:** the firmware code and keys stay out of reach. The valuable, reachable target – the control protocol – is already fully mapped.

## Still open, low risk

- **Bluetooth HCI capture** of the QCY app on Android (developer options → "Bluetooth HCI snoop log"), analyze in Wireshark. Best way to cross-check real command sequences (EQ, ANC, key remap) against our docs.
- **Full characteristic discovery** (no UUID filter): confirm whether the N70 exposes `0007` (fw version), `0009` (prompt language), `000D` (key remap) etc. that the app defines – read only.
- **Remaining unknown fields**: settings blob `48`; advertisement bytes 2, 4, 8–10, 19. Map by observing state changes.
- **EQ**: confirm iitType `3` vs `2` by a listening test; check whether the master gain is audible; whether writing a preset `id` (1–14) makes the device load its own stored curve (read first, keep the original).

## High risk / big effort

- **Read-only `0x02` device-info query over 7033** would give the real firmware version from the device – but it still means writing to service 7033, which our rules forbid. Only with saved state, explicit intent, read-back, and never the OTA write opcodes.
- **Custom firmware / LE Audio** (the chip supports BLE Audio; the firmware doesn't offer it): needs the SDK, weeks–months, bricking risk. Spare unit only.

## Don't

- Try unknown opcodes (factory reset, delete pairings, power off: `01/02/03/0D/14`).
- Write to service 7033 (OTA/CLI) – the CLI channel has FORCE_CRASH / SOFT_RST / SET_KV.
- Flash anything until the image format and a recovery path are understood.

## Custom firmware feasibility / the ADK (2026-11-10)

The N70 is built with WuQi's **`wq-adk` version 1.3.6.27** (from the firmware build tag; `components/` layout + `wqcore`, a newer generation than the public `sdk_tws_6.1.0.295` / ZT210 tree). Searched for the matching/compatible ADK across GitHub, Bing, Baidu and Gitee:

- **Not publicly available.** The full `wq-adk` / `wq-audio` package is vendor-delivered under NDA (stated outright by multiple sources). Baidu and Gitee search are login/bot-walled; Bing surfaces no leak, and the exact package names (`wq-audio_1.4.0.69`, `wq-adk_1.3.6`) return zero results.
- The **toolchain is gated too**: Cadence Xtensa (xt-clang, RI-2020.4) needs a license from WuQi's download server, plus `xtensa-wuqi-elf-gcc 12.2`, RISC-V GCC 14.2, and NeuroWeave/XNNC for the NPU.
- Public **reference material** that assumes you already have the ADK (useful if it were ever obtained): [qqq5127/ZT210](https://github.com/qqq5127/ZT210) (older-gen full source, structural reference), [haikow/silero-vad-test](https://github.com/haikow/silero-vad-test) (build flow + toolchain list + patches against `wq-adk 1.4.0.69` for a 7036), [TommyLITommy/WUQI_SDK_Learning_And_Recording](https://github.com/TommyLITommy/WUQI_SDK_Learning_And_Recording) (deep wq-adk internals notes incl. the POGO-pin single-line flashing flow), and a CSDN article on the older `wq_sdk_env` Windows build env.

Bottom line: building N70-compatible firmware is gated on three things we don't have and can't get without being a WuQi customer — the NDA ADK package, the licensed toolchain, and the N70 board config — plus physical test-pad flashing. See the feasibility discussion under "High risk / big effort" above.

The full development-platform + earbud-architecture picture is consolidated in [dev_platform.md](dev_platform.md) (SDK, toolchain, build/package/flash pipeline, the three cores + DSP, debug/UART, case).

**Custom firmware is being actively pursued** ([custom_firmware.md](custom_firmware.md)): the N70 has **no secure boot and no image signing** (boot checks only the guard magic `0xA4E49A17`; OTA checks only magic + CRC-32; shipping images are unsigned, `tlv_count=0`). So a repacked, modified image with valid CRC-32s will boot — custom firmware is feasible at the binary level, flashable over OTA (service 7033) or single-wire UART, with a UART read-back as the recovery net.

## Open next steps (state 2026-11-20)

**Extend the touch keys (no flashing needed, probably).** The firmware's touch-function switch implements 16 funcIds; the app exposes only 9. Hidden funcIds: 8, 9, 10, 16, 17, 18, 21, 22, 23 (details + patch points in [patch_targets.md](patch_targets.md), source: static disassembly, not device-verified). Next:
1. Statically trace what each hidden funcId actually does (rule out power-off / factory reset / pairing wipe).
2. Isolate the char `000D` write handler: does it range-check funcId?
3. Only then, with the user's go-ahead: test harmless ones via a raw `000D` write `[eventID, funcId]` — save original mapping, write, read back, restore.

**Swap sounds.** Spoken prompts ("adaptive ANC on", "battery low…") are factory-flashed outside the OTA image; beeps are in the in-OTA "MOqW" container (undecoded). Both need a UART flash dump first — see [tone_prompts.md](tone_prompts.md).

**MeloBuds Pro as UART rig (sacrificial unit, user-authorised).** Opened, PCB shows >10 test pads. Next hardware session (user present): classify pads with a multimeter (GND by continuity, VBAT/rails by DC volts, rest = UART/single-wire candidates), then listen read-only with [`tools/uart_listen.py`](../tools/uart_listen.py) (never transmits; baud sweep 115200 / 921600 / 1500000 / 2000000 / 3000000). WuQi UART may be 1.8 V — check the adapter or use a level shifter. Nice to have: 8-ch logic analyzer, a spare N70.

**Pulse from the in-ear (feedback) ANC mic — idea, undecided.** Physically plausible: occlusion effect; Google's APG (2023) measures heart rate via the ANC feedback mic; Martin & Voix (IEEE TBME 2018) got heart/breathing rate from an in-ear mic. The N70 already uses the feedback mic for fit detection (opcode `0x11`). But stock firmware only exposes the outer, noise-suppressed HFP mic, so this needs a DSP-image (Xtensa HiFi5) patch to route the raw feedback mic or compute BPM on-device. Possible cheap pre-test: record HFP audio on the Mac with the bud in the ear and look for a ~1 Hz component (likely filtered out). Possible worker: scout the DSP image for the feedback-mic / fit-detection path.

**User-side, async:** an Android HCI snoop log of a real OTA update + a control session would sharpen [ota.md](ota.md).

Out of scope by user decision: LC3 / new codecs (not feasible), call-quality/ENC work (user is happy with the mic).

## Related

- LDAC from a Mac: macOS only does SBC/AAC; a custom A2DP/AVDTP over IOBluetooth L2CAP might work (unverified).
- LE Audio: the Mac supports it (`LEA`), but the N70 **cannot** – the firmware has no LC3 codec, no isochronous (CIS) path and no LE Audio GATT profiles; it is classic-BT-only (A2DP/AVRCP/HFP). See [firmware_internals.md](firmware_internals.md). Confirmed from the decompressed firmware, not just the GATT scan.
