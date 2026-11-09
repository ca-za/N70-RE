# Open questions and next steps

## Done (2026-11-09/10)

1. **QCY app decompiled** (jadx, `work/qcy-app-4.0.7-jadx/`): full opcode table → [protocol.md](protocol.md); OTA over service 7033 → [ota.md](ota.md); firmware is downloaded from a server, not in the APK → [firmware.md](firmware.md).
2. **Firmware obtained**: HT18 3.0.13, encrypted → [firmware.md](firmware.md). Internal model HT18 confirmed.
3. **N70 server control panel** fetched → [controlpanel.md](controlpanel.md): confirms which opcodes the N70 supports, ANC values, EQ presets. Resolved `0x19` (prompt language), `0x1F` (auto power-off), `0x04` (play state), and that `0x2A` (wind) is live.

## Firmware decryption – researched, not feasible without more access

The OTA `.bin` payload is encrypted (whole-file entropy 8.000, no ECB block repeats → stream/CBC, likely compressed then encrypted; Wuqi says the OTA package is compressed). Only the ~0x90-byte header is plaintext. The chip validates and decrypts it on device (OTA errors "encryption key mismatch", "uboot mismatch").

What the research turned up (see [sources.md](sources.md)):
- **No public key, tool or prior analysis** for WQ7033 firmware. The Wuqi SDK (with `app_wqota.c` and the PC packaging tool) is NDA-only, for device makers.
- The **build artifact is a `.wpk`** file – a RAR-like container that holds plaintext config (`app_evt.xml`, `audmap_config.json`) and the image regions (e.g. `tws_core0`, uboot). Community blogs rename `.wpk` → `.rar` to peek inside. **But that is the build output, not our file** – our `*-OTA.bin` is the *exported, packed/encrypted* image, which is not a RAR and has no plaintext payload.
- So the readable config only exists inside the original `.wpk`, which we don't have.

Realistic ways to get the firmware code, all high effort / out of current scope:
- Obtain the Wuqi SDK + packaging tool under NDA (device makers only), or a leaked SDK.
- Hardware attack on a **spare** unit: flash dump (external SPI/eMMC read), JTAG/SWD, or voltage/EMFI glitching to capture the decrypted image or the key from RAM. Risk of bricking; needs a sacrificial device and lab gear.
- Capture the chip pulling plaintext during its own decrypt – not exposed over any interface we can reach.

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

## Related

- LDAC from a Mac: macOS only does SBC/AAC; a custom A2DP/AVDTP over IOBluetooth L2CAP might work (unverified).
- LE Audio: the Mac supports it (`LEA`), the N70 offers no LE Audio services.
