# N70 control panel (server feature list)

The QCY app has no N70-specific code; which features a model exposes comes from a per-model "control panel" JSON the app downloads. This is the **N70's own panel** – the authoritative list of what the N70 firmware supports and the exact commands the app sends it. Raw JSON: `data/controlpanel_n70.json`.

How it was fetched (guest token, see [firmware.md](firmware.md) for the token step):
```
POST https://api.watch.qcy.com/product/findControlPanels     (NOT appcontent.qcy.com)
Authorization: Bearer <guest token>
form: modelId=23877, firmwareVersion=3.0.13
```
Valid for firmware `0.0.0`–`999.999.999`. **This is not device-verified**, but it is QCY's own description of this exact model, so it is far stronger than the generic app code.

## Features the N70 exposes

Each panel item carries a `cmdid` = the **decimal A001 opcode**. This cross-confirms our opcode table (see [protocol.md](protocol.md)).

| Panel item | cmdid (hex) | Notes |
|---|---|---|
| Customizing button function | char `000D` | key remap, see below |
| Noise canceling mode | 23 → `0x17` | ANC / transparency / normal, see below |
| Sound effect (EQ) | 34 → `0x22` | 8 presets + personalized, see [eq.md](eq.md) |
| Sound channel balance | 22 → `0x16` | |
| Find headset | — | plays a sound; no earbud opcode |
| Tone Switch (voice-prompt language) | 25 → `0x19` | English pack `WQ00` / Chinese `WQ01` (written as ASCII "57513030" / "57513031") |
| Rename device | → `0x18` | |
| Timing power-off | 20 → `0x14` | countdown shutdown |
| Fit detection | 17 → `0x11` | ear-tip seal test |
| Wear detection | 44 → `0x2C` | + sensitivity Medium/Normal/High |
| Beep volume | 29 → `0x1D` | levels exposed: 4 / 6 / 8 / 10 (of 15) |
| Disconnect-and-power-off | 31 → `0x1F` | u16 LE minutes, keys `0500`=5, `0A00`=10, `1E00`=30, `3C00`=60, `FFFF`=never |
| Gaming mode | 9 → `0x09` | `FF03090101` on / `FF03090102` off |
| Wind noise detection | 42 → `0x2A` | `FF032A0101` on / `FF032A0100` off — **0x2A is live on the N70** (the generic app code didn't define it) |
| Sleeping mode | 16 → `0x10` | `FF03100101` / `FF03100102` |
| LDAC switch | 35 → `0x23` | `FF03230101` / `FF03230102` |
| Dual device (multipoint) | 36 → `0x24` | `FF03240101` / `FF03240102` |
| Firmware update | — | OTA, see [ota.md](ota.md) |
| Reset to default | → | `FF020100` ⚠ |
| Reset to factory | → | `FF020300` ⚠ |

The N70 panel has **no** spatial-audio, head-gesture, AI-ANC, hearing-health or find-my opcode item – those exist in the app but are not offered for this model.

## Key remap (char `000D`)

eventIDs (write raw `[eventID, funcId]` pairs): touch L/R = 1/2, double = 3/4, triple = 5/6, long press = 9/10. Functions offered on the N70: 0 none, 1 play/pause, 2 prev, 3 next, 4 voice assistant, 5 vol+, 6 vol−, 7 gaming, **11 ANC mode**. (Note: on the N70 the only functions are these; "11 = ANC mode", not the generic app's "11 = redial".)

Factory defaults: single = none, double = play/pause, triple = prev (L) / next (R), long = voice assistant (L) / ANC mode (R).

## ANC command values (opcode 0x17)

The panel gives ANC states as 24-bit `cmdid` values = the packed 3-byte parameter `mode<<16 | scene<<8 | level` of opcode `0x17` (`FF 05 17 03 <mode> <scene> <level>`). This confirms every mode and adds the level ranges:

| Mode | cmdid range (hex) | bytes `mode scene level` |
|---|---|---|
| Adaptive ANC | `010500` | `01 05 00` (single value) |
| Indoor | `010100`–`010102` | `01 01 00..02` |
| Commuting | `010200`–`010202` | `01 02 00..02` |
| Noisy | `010300`–`010302` | `01 03 00..02` |
| Anti-wind | `010400` | `01 04 00` |
| Transparency | `030100`–`030106`, default `030104` | `03 01 00..06` (level 0–6) |
| Normal (off) | `020000` | `02 00 00` |

So the "level" byte is a slider: 0–2 for the fixed ANC scenes, 0–6 for transparency. All match our device-verified `0x17` writes.
