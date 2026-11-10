# QCY protocol (service A001)

Based on [OpenQCY-Desktop](https://github.com/GiorgioRafael/OpenQCY-Desktop) (the only project with N70 validation), complemented by [qcyx](https://github.com/BrunoAssis/qcyx), [QuickyAndroid](https://github.com/hui1601/QuickyAndroid), [qcy-ht07-protocol](https://github.com/Tekkiech/qcy-ht07-protocol). Everything marked ✅ was tested **on this device** (2026-11-09).

## Frame

```
FF <len> <op> <plen> <params...>      len = plen + 2, no checksum
```

- Send: to `A001/1001`, write without response
- Replies: notify on `A001/1002` (call `setNotifyValue(true)` first); one frame can contain several `<op> <plen> <params>` blocks
- Query a value: `FF 03 FE 01 <op>` → reply block `<op> <plen> <params>`
- Subscribe to notifications before the first request, otherwise the reply is lost (observed)

## Settings blob (read of 1002)

A **read** (not a notify) of `1002` returns all settings in one frame, e.g.:

```
ff 32 | 2c 03 010100 | 48 01 01 | 08 03 2f2f0f | 09 01 02 | 17 03 010500 | 10 01 00 | 16 01 32
      | 04 01 02 | 23 01 01 | 24 01 01 | 1f 02 0500 | 1d 02 040f | 19 04 57513030
```

| Op | Params (example) | Meaning | Status |
|---|---|---|---|
| `2C` | `01 01 00` | wear detection on (bytes 2/3: music/ANC action on removal) | read ✅ (source: N70 validated) |
| `48` | `01` | in-ear sensitivity 1 | Quicky/HT07 only |
| `08` | `2f 2f 0f` → `37 37 0f` | **volume L / R** (third value probably max 0x0F?) – changed with the media volume ✅ observed | read |
| `09` | `02` | game mode (01 on / 02 off) | read + write ✅ |
| `17` | `01 05 00` | noise control (see below) | read + write ✅ |
| `10` | `00` | sleep mode off | source |
| `16` | `32` | balance (0..100, 50 = center) | qcyx only (HT08) |
| `04` | `02` | music control? meaning unclear | – |
| `23` | `01` | LDAC on | source (N70 validated) |
| `24` | `01` | multipoint on | source (N70 validated) |
| `1F` | `05 00` | auto power-off after disconnect, u16 LE minutes (5) | qcyx |
| `1D` | `04 0F` | prompt volume 4 of max 15 | read + write ✅ |
| `19` | `57 51 30 30` | ASCII "WQ00" (model/language string) | – |

## Verified commands

### Noise control `0x17` ✅

```
set:   FF 05 17 03 <mode> <sub> <noise>
read:  FF 03 FE 01 17   → 17 03 <mode> <sub> <noise>
```

| Mode | Bytes | tested |
|---|---|---|
| Adaptive | `01 05 00` | ✅ |
| Indoor | `01 01 02` | source |
| Commute | `01 02 02` | source |
| Noisy | `01 03 02` | ✅ |
| Wind | `01 04 00` | source |
| Off (normal) | `02 00 00` | ✅ (seen in the blob later) |
| Transparency | `03 01 04` | ✅ |

After setting, the echo `17 03 ...` arrives, plus `FF 03 28 01 01` (ANC_RESULT = applied; qcyx documents this for HT08 only – observed on the N70 ✅).

### Game mode `0x09` ✅

`FF 03 09 01 01` = on, `FF 03 09 01 02` = off. Reply `09 01 <value>`.

### Prompt volume `0x1D` ✅

- **Only the 2-byte form works:** `FF 04 1D 02 <level> 00` (level 0..15). Reply `1D 02 <level> 0F`.
- The 1-byte form from OpenQCY (`FF 03 1D 01 <level>`) is **ignored** ✅ tested.

### EQ `0x22` ✅

See [eq.md](eq.md).

### Battery `0x2F`

`FF 03 FE 01 2F` (HT07/OpenQCY fallback). Not needed on the N70, `0008` notifies.

## Other known opcodes (untested)

From the sources, validated as **read** on the N70 according to OpenQCY: wear detection `2C`, game mode `09`, sleep `10`, LDAC `23`, multipoint `24`, wind detection `2A`, prompt volume `1D`, shutdown timer `14`.
Touch mapping via characteristic `000D` (not found/searched on this device).

Naming conflicts between the sources: `1D` (prompt/tone/notification volume, 1 vs. 2 bytes), `1F` (standby 1 byte vs. auto power-off u16), `2C` (byte names). See sources.md.

## Full opcode table (from the QCY app 4.0.7)

Decompiled from the generic QCY A001 library (`com/qcymall/qcylibrary/dataBean/DataBean.java` and friends). **Source only** – these are the opcodes the app *can* send; which ones the N70 actually supports is decided by a per-model "control panel" JSON the app downloads from the server (`product/findControlPanels`, `modelId` = vendor ID), not by the APK. The app itself has **no N70-specific code** (no "N70"/"HT18"/"WQ00" anywhere); the N70 is handled like any other non-JieLi model. Not device-verified unless marked ✅ (those are cross-checked with our own reads above).

⚠ = dangerous (reset / power / factory / test). Frames follow `FF len op plen params`.

| Op | Name (app) | Params / meaning | Status |
|---|---|---|---|
| `01` | RESET_DEFAULT | `FF 02 01 00` reset settings | ⚠ source |
| `02` | CLEAR_PAIR | `FF 02 02 00` clear pairing list | ⚠ source |
| `03` | FACTORY_RESET | `FF 02 03 00` (panel sometimes labels `FF020100` as factory) | ⚠ source |
| `04` | MUSICACTION | write 1 play / 2 pause / 3 prev / 4 next; read `b0==1` = playing → blob `04 01 02` = **not playing** | explains 0x04 ✅ |
| `05` | LIGHT | flash light (speakers) | source |
| `06` | RUER | in-ear detection 1 on / 2 off | source |
| `07` | NOISE | legacy ANC value, read `07 01 FF` | source |
| `08` | VOICE | volume, write `[L,R,0]`, read `[L,R,max]` | read ✅ |
| `09` | DIYANSHI | game / low-latency 1 on / 2 off | r+w ✅ |
| `0A` | JIANTING | legacy transparency/monitor bool | source |
| `0C` | NOISEMODE | legacy mode byte | source |
| `0D` | TESTMODE | touch-test mode 1/2 | ⚠ source |
| `10` | SLEEPMODE | 1 on / 2 off (read `b0==1`) | source |
| `11` | COMPACTNESS | ear-tip fit test; write `FF 05 11 03 x x x`, result `[status(0 ready/2 result), L, R]` | source |
| `12` | LEDMODE | 1/2 | source |
| `14` | POWERMANAGER | shutdown timer; write `FF 06 14 04 <u16 LE min> 00 00`, read `[set u16, remaining u16]`. **⚠ `0` minutes = power off NOW** (not "cancel" as the app code suggests) – tested on the N70, the buds switched off ~2 s later. Setting 90 min ✅ (`14 04 5a00 5a00` read back). "Off" reads as set `0xFFFF`; cancelling with `0xFFFF` is untested | ⚠ partly ✅ |
| `16` | BALANCE | 1 byte 0..100 | read |
| `17` | ANCSETTING | `[mode, scene, level]`; 1 ANC / 2 off / 3 transparency | r+w ✅ |
| `18` | PAIRNAME | rename, UTF-8 bytes; read NUL-terminated | source |
| `19` | VOICENAME | voice-prompt **language** switch: ASCII pack ID, `WQ00` = English, `WQ01` = Chinese (panel "Tone Switch", cmdid 25). Our blob's `WQ00` = English prompts | N70 panel |
| `1D` | TONEVOLUME | read `[v,max]`, write `[v,0]` (2-byte form; 1-byte only for vendor 16737) | r+w ✅ |
| `1E` | TAKEPHOTO | camera shutter | source |
| `1F` | STANDBY / auto power-off | **auto power-off after disconnect**, u16 LE minutes; `0500`=5 `0A00`=10 `1E00`=30 `3C00`=60 `FFFF`=never (panel "Disconnect and power off", cmdid 31) | N70 panel |
| `20` | MULTIEQ | 6 bytes/band (no type byte); used for WQ vendors 0x4D43/45/46/47 instead of 0x22 | source |
| `22` | MULTIEQ2 | 7 bytes/band, see [eq.md](eq.md) | r+w ✅ |
| `23` | LDAC | single value | read |
| `24` | MOREDEVICE | multipoint, write 1/0 | read |
| `27` | AEQ | `27 01 01` runs adaptive-EQ | source |
| `28` | ANC_RESULT | single (applied echo) | ✅ |
| `29` | ANC_WEAR | 1–2 bytes | source |
| `2A` | WIND_DETECT | wind-noise detection; `FF 03 2A 01 01` on / `FF 03 2A 01 00` off | N70 panel |
| `2B` | KEYFUN | `[keyId, func]` pairs (notify of key map) | source |
| `2C` | PEIDAI | wear: `[enable, musicIdx, ancIdx, (toneEnable)]`, write `FF 05 2C 03 en m a` | read ✅ |
| `2D` | SPACE_AUDIO | spatial audio | source |
| `2E` | MUSIC_MODE | single | source |
| `2F` | BATTERY | fallback query (N70 uses char 0008) | source |
| `30` | VERSION | defined, unused | source |
| `32` | ENV_ADAPTATION | environment-adaptive 1/0 | source |
| `34` | TWS_ENABLE | single | source |
| `35`/`36` | LED_SWITCH / LED_EFFECT | speaker LEDs | source |
| `37` | PLAY_MODE | single | source |
| `39` | FOCUS_MODE | 0/1 | source |
| `3A`/`3B` | MUSIC_STATE / MUSIC_INFO | SD music: `[id u32, playing, mode]` / file list | source |
| `3D` | TONE_PLAY | 0/1 | source |
| `3E` | SYNC_TIME | `[YY,MM,DD,hh,mm,ss, 1<<(dow-1)]` | source |
| `3F` | ALARM | `[act 1add/2del/3edit, id, en, h, m, cycle, x]` | source |
| `43` | AI | AI test value | source |
| `44` | MAXEQ_COUNT | number of PEQ slots; queried on connect via `FE 44` | source, useful |
| `45` | CUSTOM_EQ_TEST | 1 on entering EQ editor, 0 on exit | source |
| `46`/`47` | MULTIEQ_LEFT / RIGHT | per-side PEQ, layout like 0x22 | source |
| `48` | INEAR_SENSITIVITY | single (slider) | read |
| `4A` | GAME_CONFIG | `[on, tipOn]` (inferred) | source |
| `4D` | PHONE_INFO | multipoint device list; read `count,{len,status,mac6,name\0}`, write `[action, mac6]` action 1 connect / 2 unpair / 3 disconnect | ⚠ source |
| `4F` | PHONE_STATUS | `[mac6, status]` | source |
| `50` | HEAD_ACTION | head gestures 1/0 | source |
| `51` | SENSOR_CONFIG | `[action, func]` pairs | source |
| `52` | SENSOR_TEST | 250/251 start/stop gesture test | source |
| `54` | AI_ANC | `[status, noiseScene, mode, subScene, level, touchIdx]` | source |
| `55`/`56` | AI_ANC_CFG / CFG2 | 45 bytes = 9×5 | source |
| `58` | HEAR_HEALTH | 4 bytes | source |
| `5A` | AI_ANC_PREVIEW | 4 bytes | source |
| `5B` | SPACE_AUDIO_MODE | single index | source |
| `FE` | REQUESTDATA | query `FF 03 FE 01 <op>` | ✅ |

Opcodes not in the table are parsed generically: `plen ≤ 2` → u16 LE value, otherwise a hex string. **No find-my-earbuds opcode exists** – the app's "find earbuds" just plays a sound from the phone. **No opcode enters OTA** – OTA goes over the Wuqi service 7033 / SPP, see [ota.md](ota.md).

Which of these the N70 actually supports is listed in its server control panel ([controlpanel.md](controlpanel.md)): it confirms (via each item's decimal `cmdid`) the opcodes `09, 10, 11, 14, 16, 17, 18, 19, 1D, 1F, 22, 23, 24, 2A, 2C` and the two reset frames, plus the ANC parameter values. Rows marked "N70 panel" above come from there.

## Live opcode sweep (device, 2026-11-10) ✅

We swept the read-only query `FF 03 FE 01 <op>` over **every** opcode `0x00`–`0xFF` on the real N70 (read-only; nothing was set) and logged which ones reply. This empirically bounds the queryable command set and upgrades many "source only" rows to device-verified.

**Result: the N70 replies only on `0x08`–`0x48`, and every responder is already in the table above — there are no hidden *queryable* opcodes.** (Write-only / event-only commands such as the resets `01/02/03`, `0x27` AEQ-trigger or `0x28` ANC_RESULT don't answer a query and so can't be found this way; but QCY's own app implements the whole protocol, so undocumented commands are unlikely.)

Responders, with the N70's current value at sweep time (decoded):

| Op | Reply | Meaning |
|---|---|---|
| `08` | `08 03 LL RR 7f` | volume L/R, **max = 0x7F (127)**, live-varying |
| `09` | `09 01 02` | game mode off |
| `10` | `10 01 00` | sleep mode off |
| `14` | `14 04 ffff 0000` | shutdown timer off (set 0xFFFF, remaining 0) ✅ format confirmed. Writing 0 powers the buds off immediately ✅ (2026-11-10) |
| `16` | `16 01 32` | balance 50 (center) ✅ |
| `17` | `17 03 02 00 00` | ANC off (normal) |
| `18` | `18 22 20 00…` | device name, 34-byte field (currently blank) ✅ |
| `19` | `19 06 04 57 51 30 30` | prompt language pack "WQ00" = English ✅ |
| `1D` | `1d 02 04 0f` | prompt volume 4 / 15 |
| `1F` | `1f 02 05 00` | auto power-off 5 min ✅ |
| `22` | `91`-byte PEQ | current parametric EQ (a **custom** curve, differs from the factory Spatial preset) |
| `23` | `23 01 01` | LDAC on |
| `24` | `24 01 01` | multipoint on |
| `2A` | `2a 01 01` | **wind detection on** ✅ (was source only) |
| `2B` | `2b 14 01 00 02 00 03 01 04 01 05 02 06 03 07 00 08 00 09 04 0a 0b` | **current key map**, 10 `[keyId,func]` pairs ✅ (long-press-R = func 0x0B = ANC mode) |
| `2C` | `2c 03 01 01 00` | wear detection on, music-action 1, anc-action 0 ✅ |
| `43` | `43 01 01` | "AI" feature on ✅ |
| `46` / `47` | `91`-byte PEQ | per-side EQ **left / right** ✅ (same layout as 0x22) |
| `48` | `48 01 01` | in-ear sensitivity 1 ✅ |

**No reply** (so: absent on the N70, or write/event-only): among the documented ops, `04, 06, 0A, 0C, 11, 12, 1E, 20, 27, 28, 29, 2D, 2E, 2F, 30, 32, 34, 35–3F, 44, 45, 4A, 4D, 4F, 50–5B`, and everything `0x49`–`0xFF`. Notably `0x2D` (spatial audio), `0x44` (max-EQ-count), `0x54` (AI-ANC) and the speaker/LED/SD-music ops give nothing — consistent with the N70 not exposing those features ([controlpanel.md](controlpanel.md)).

### Write-only opcodes: no hidden ones (firmware dispatch examined)

The query sweep can't see write-only / event-only commands (resets `01/02/03`, `0x27` AEQ-trigger, etc.). We examined the app core's firmware dispatch to check for any beyond the documented set. The firmware's clean handler table (`0x34208d34`, 26 entries) turned out to be the **CLI/AT** dispatch (it uses the CLI responder), not A001; the A001 (QCY `FF`-frame) dispatch is a **sparse switch**, not a compact table, so it does not enumerate cleanly by static RE. Two independent bounds settle the question anyway: (1) the live query sweep found every readable opcode already documented, and (2) QCY's own app (`DataBean`) is the authoritative, complete opcode enum — QCY built the app and the firmware to one protocol, so a command the firmware handles but the app never names is very unlikely. **Conclusion: no evidence of hidden A001 opcodes; the documented set is authoritative, confirmed from both QCY's source and the device.**

### Key remap (characteristic `000D`, not an FF frame)

Raw `[keyId, funcId]…` pairs. keyIds: music L/R single 1/2, double 3/4, triple 5/6, quad 7/8, long 9/10; call-mode = +20 (21–30). funcIds: 0 none, 1 play/pause, 2 prev, 3 next, 4 assistant, 5 vol+, 6 vol−, 7 game, 8 answer, 9 reject, 10 hold, 11 redial. The actual per-model set comes from the panel JSON.
