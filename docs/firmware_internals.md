# Firmware internals (decompressed images)

From the unpacked OTA image ([firmware.md](firmware.md)). Each image starts with a 32-byte `iot_flash_image_header_t` (from the WuQi ADK, `iot_boot_map.h`):

```
guard(4)=0xA4E49A17  length(4)  version(4)  start(4)=entry/run addr  crc(4)  tlv_count(1)  reserved(11)
```
Code begins at file offset `0x20`, i.e. run address `start`. CPU core images are **RISC-V RV32IMAFC** (confirmed: the entry matches the ADK `start.S` exactly — trap disable, GP/SP setup, FPU init). The DSP image is **Xtensa (Cadence HiFi 5)**.

## Image / memory map

| Pack idx | Flash LMA | Run addr (entry) | Arch | Role (from strings) |
|---|---|---|---|---|
| 0 | `0x000002` | — | — | boot/partition map (304 B, `iot_boot_map`), not code |
| 1 | `0x010000` | `0xB4010020` | RISC-V | **Bluetooth core**: controller + host, A2DP / AVRCP / HFP, `bt_dp_le_audio.c`, RPC |
| 2 | `0x0AB000` | `0x26008000` | Xtensa HiFi5 | **DSP**: audio processing (`wq aec/drc/eq/es/volume`), LDAC decode |
| 3 | `0x169000` | `0x34169020` | RISC-V | **Application core**: `qcy_app.c` – the A001 protocol logic, BT RPC user cmds |
| 4 | `0x3EE000` | — | data | config (7 KB) |
| 5 | `0x3F0000` | — | data | tone / voice prompts (`WQ7036`, `QCY MeloBuds N70`) |

Two RISC-V CPUs (BT + application) plus the Xtensa HiFi5 DSP – matches the datasheet's "2× RISC-V + HiFi 5 DSP". Code runs at `0xB401xxxx` (BT), `0x34xxxxxx` (app); global data/`_gp` is in the `0x02xxxxxx` region (copied from flash at boot).

## Loading in radare2

The images are raw (no ELF). Map at the base = `start - 0x20` and seek to `start`:

```sh
# application core (qcy_app)
r2 -a riscv -b 32 -m 0x34169000 work/.../extracted/app_core_riscv_0x00169000.bin
> e asm.bits=32; s 0x34169020; aa; afl

# bluetooth core
r2 -a riscv -b 32 -m 0xb4010000 work/.../extracted/bt_core_riscv_0x00010000.bin

# DSP (Xtensa)
r2 -a xtensa -m 0x26007fe0 work/.../extracted/dsp_hifi5_xtensa_0x000ab000.bin
```

Ghidra: import raw, language `RISCV:LE:32:RV32IC` (or `RV32GC`), base address as above. String rodata is inside each code image, so `la`/`auipc+addi` cross-references resolve once the base is right.

## Findings so far

- **LE Audio is not usable on the N70 and cannot be enabled by flipping a flag.** The BT core has two orphan host-layer file strings (`bt_dp_le_audio.c`, `aud_sv_lea.c`), but the parts that make LE Audio *work* are absent:
  - **No LC3 codec** anywhere in the firmware (0 string hits across all images) — LC3 is mandatory for LE Audio.
  - **No isochronous (CIS/CIG/BIS/ISOAL) data path** — no such strings.
  - **No LE Audio GATT profiles** (ASCS / PACS / BAP / BASS) compiled in.
  - Classic Bluetooth audio is fully present instead: A2DP, AVRCP, HFP (`T_a2dp_*`, `T_avrcp_*`, `T_hfp_*`).
  So the N70 is classic-BT-only, matching the GATT scan ([gatt.md](gatt.md)) and `system_profiler`. Enabling LE Audio would need a different firmware built with the Wuqi ADK (NDA toolchain) that includes LC3 + ISO + the LE Audio services — not something a config flag or binary patch can add. The ZT210 SDK snapshot we have contains no LE Audio source at all.
- **Codecs present:** LDAC (decoder), AAC, SBC, CVSD / mSBC (calls). No aptX.
- **The A001 command handler** is `qcy_app.c` + `app_user_cmd.c` / `app_user_event.c` on the application core (img3). Log strings name real handlers: `qcy_to_wuqi_language_set`, `handle_update_bt_name`, `notify_lang_name`, `notify_local_name`, `notify_fix_test_result`, `handle_get_bredr_linkkey`, `set_default_name`.
- **Build identity:** `QCY_HT18-7035AX-B-ADK_1.3.6.27-LDAC-20251219`, `FW-VERSION-v0.3.0.13`, project path `/root/projects/HT18/wq-adk/`.

## Keyword spotting / voice — none on the device

The WQ703X datasheet advertises "keyword spotting in low power" and an NPU, so the question was whether the N70 listens for a wake word. **It does not.** Searched all images: no `kws` / `keyword` / `hotword` / `wake-word` / `vad` / on-device ASR / NPU-model strings at all. The WuQi ADK source likewise has no KWS/hotword module, and nothing drives the NPU for voice (the `wakeup` symbols are all low-power wake *sources*: RTC / WIC / GPIO / timer).

The only voice strings in the firmware are HFP AT commands: `+VR` (standard HFP `AT+BVRA` voice-recognition activation) and `+APLSIRI` / `AT+APLSIRI?` (Apple's HFP extension to invoke Siri). So the N70's "voice assistant" is **tap-to-invoke the phone's assistant**: a touch gesture (key-remap function 4) tells the *phone* to start listening; recognition happens on the phone (Siri / Google), never on the earbud. There is nothing the earbud reacts to by voice — no always-on listening, no wake word.

Where the chip's AI/DSP compute actually goes: **call noise reduction** (the "3-mic AI ENC" — DSP libs `wq aec` / `wq es` / `wq med`) and ANC, not keyword spotting. The N70 simply doesn't ship the chip's KWS capability.

## Factory CLI (hidden command interface)

A whole command interface lives on service 7033 that the app never exposes — see [factory_cli.md](factory_cli.md). Documentation only; **7033 is write-forbidden** by project rules and many of its commands are destructive.

## Open / next

- Disassemble `qcy_app` on the app core and map the full A001 opcode dispatch, to cross-check [protocol.md](protocol.md) against the firmware.
- LE Audio enablement: **answered – not feasible** (no LC3 codec, no ISO path, no LE Audio GATT profiles in the firmware; see above).
- DSP image: Xtensa HiFi5, would need the right Xtensa config for clean disassembly.
