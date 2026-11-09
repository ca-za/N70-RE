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

From the sources, validated as **read** on the N70 according to OpenQCY: wear detection `2C`, game mode `09`, sleep `10`, LDAC `23`, multipoint `24`, wind detection `2A`, prompt volume `1D`, auto power-off `14`.
Touch mapping via characteristic `000D` (not found/searched on this device).

Naming conflicts between the sources: `1D` (prompt/tone/notification volume, 1 vs. 2 bytes), `1F` (standby 1 byte vs. auto power-off u16), `2C` (byte names). See sources.md.
