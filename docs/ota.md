# OTA / Wuqi service 7033

Source: static analysis of the QCY app 4.0.7 Wuqi SDK (`org/wuqi/android/...`), cross-checked against the device-side WuQi ADK source on GitHub ([qqq5127/ZT210](https://github.com/qqq5127/ZT210)). **Source only, nothing here was sent to the device.** Service `7033` is write-protected by our rules — this document is for understanding, not for sending.

See also [firmware.md](firmware.md) for the image format and extraction (the OTA payload is LZMA-compressed, not encrypted), [gatt.md](gatt.md) for the service list.

## Channels under 7033

The 128-bit UUID is `00007033-0000-1000-8000-00805F9B34FB`. The SDK defines two channels on it:

| Channel | Write | Notify | Purpose |
|---|---|---|---|
| OTA | `2001` | `2002` | firmware update + a read-only device-info query |
| CLI | `1001` | `1002` | Wuqi factory/debug command line |

The `1001`/`1002` short UUIDs are the **same numbers** as QCY's A001 characteristics, but under service 7033 they are the Wuqi CLI, not the QCY protocol. Over classic Bluetooth (SPP/RFCOMM) the same roles use `7034` (OTA), `7033` (CLI), `7035` (log dump). **The shipping QCY app actually runs WQ firmware OTA over SPP `7034`, not over BLE.** The BLE OTA path exists in the SDK but is not exercised by the app.

To confirm the channel layout on the N70, enumerate the characteristics under 7033 (expect at least 2001/2002, possibly 1001/1002). `tools/list_7033.swift` lists them (reads/writes nothing).

## OTA framing (channel 2001/2002)

Envelope, no length field and no checksum on the envelope itself:
```
70 07 6E | <body> | 33
```
Body (all multi-byte fields big-endian):
```
Request : C0 | OP | LEN(2) | SN | params...     LEN = 1(SN) + len(params)
Response: 00 | OP | LEN(2) | STATUS | SN | data...
```
- `SN` is a 1-byte sequence number, incremented per command; a response is matched to its request by SN. Reset to 0 for the device-info query and at the start of the data phase.
- Firmware chunks optionally carry a trailing **CRC-32** (zlib: poly 0xEDB88320, init/xor 0xFFFFFFFF, big-endian), enabled only if the device's enter-update reply requests it.
- Chunk size = MTU − 16 (− 20 with CRC). SPP uses MTU 553 → 537 bytes/chunk; BLE would use 512 → 496.
- Retransmit: a pending SN unanswered for ~10 s is resent, up to 3 times, then the upgrade aborts.

## OTA opcodes

| OP | Meaning | Notes |
|---|---|---|
| `0x02` | **device info (read-only)** | the one safe query, see below |
| `0xE1` | get file-info offset | device replies (offset, length) of the header region it wants |
| `0xE2` | can-update? | app sends the header bytes read from the file at that offset; device replies a code |
| `0xE3` | **enter update mode** ⚠ | returns first (offset, len) + needCrc32 flag |
| `0xE4` | exit update mode | defined, never called |
| `0xE5` | **firmware data block** ⚠ | `C0 E5 LEN SN OFFSET(4) DATA [CRC32]`; reply gives next (offset, len, delay_ms) |
| `0xE6` | refresh firmware status | updateResult |
| `0xE7` | change device (TWS role switch) ⚠ | |
| `0xE8` | sync firmware status | |
| `0x03` | **reboot / commit** ⚠ | `C0 03 00 02 SN 00` |

Status codes (updateResult): 0 done, 1 data verification error, 2 failed, 3 **encryption key mismatch**, 4 file error, 5 **uboot mismatch**. canUpdate codes include 0 (single backup), 3 (double backup), 1 low power, 4 out of space, 0x10 both buds disconnected, 0x12 buds in case, 0x13 single-ear can't upgrade.

## Update flow (how the app flashes)

The app does **not** parse the firmware file. The device pulls byte ranges by absolute offset; the app only reads those ranges from the .bin and sends them. All header/segment/signature/decryption checks happen on the chip.

1. `0x02` device info — check battery ≥ 50 %, read TWS state, isLeft, isDual.
2. `0xE1` → region of the image header. `0xE2` with those header bytes → device decides single vs **double backup** (status 3 = double, the only fully implemented path).
3. `0xE3` enter update mode → first (offset, len) and whether CRC-32 is required.
4. Data pump: read len bytes at offset, split into MTU-sized `0xE5` blocks, each with its absolute offset; every reply gives the next (offset, len, delay). Finished when the device replies offset 0 / len 0. Progress = offset / fileSize.
5. `0xE6` finish; for TWS either `0xE8` sync (dual) or `0xE7` change-device then repeat for the other bud.
6. `0x03` reboot to commit.

## Device-side implementation (`app_wqota.c`)

Everything below is **source only**, read from the device-side WuQi ADK at `work/zt210-sdk/core0/src/app/tws/user_app/app_wqota.c` (guarded by `#if WQOTA_ENABLED`). It confirms and sharpens the app-derived table above; line numbers are that file.

**Channel / UUIDs** (lines 66–82): service `0x7033`, BLE write char **RX `0x2001`**, BLE notify char **TX `0x2002`**; the same roles run over classic-BT SPP channel `0x7034`. An `ota_ch_t` enum (`OTA_CH_SPP`/`OTA_CH_BLE`) tracks which transport is active.

**Envelope** (lines 117–123, 171–180): the frame is a packed `packet_t`:
```
prefix:24  source:3  unused:3  need_rsp:1  is_cmd:1  opcode:8  len_be:16  data[]
```
- `prefix` = `PACKET_PREFIX_VALUE 0x6E0770` → the bytes `70 07 6E` on the wire; a 1-byte `PACKET_SUFFIX_VALUE 0x33` closes every frame.
- The byte after the prefix carries `is_cmd` (bit 7) + `need_rsp` (bit 6) + a 3-bit `source` (bits 0–2). So a request's `C0` = is_cmd + need_rsp, source 0; a response's `00` = neither. This is exactly the `C0`/`00` split noted above.
- `len_be` is the big-endian length of `data[]` (= `SN` + params). `PKT_LEN = sizeof(packet_t)=6 + len + 1(suffix)`. The parser rejects a frame whose prefix (line 1038) or suffix (line 1076) is wrong.

**Opcodes** (`opcode_t`, lines 140–154) match the table above, and add `OPCODE_OTA_CUSTOM = 0xF0` (vendor hook). The dispatch is a plain `switch` (lines 960–987).

**`status` byte** (`status_code_t`, lines 125–138) — the response's first field, distinct from each opcode's own `result` byte: `0` SUCCESS, `1` FAIL, `2` UNKNOWN_CMD, `3` BUSY, `4` NO_RESPONSE, `5` CRC_ERROR, `6` ALL_DATA_CRC_ERROR, `7` PARAM_ERROR, `8` RESPONSE_DATA_OVER_LIMIT, `9` NOT_SUPPORT, `10` PARTIAL_OPERATION_FAILED, `11` UNREACHABLE.

**Sizes / CRC** (lines 51–58): `OTA_VID 0x076E`, `OTA_PID 0x7033`; `OTA_BLOCK_LEN 512` (firmware payload bytes the device asks for per `0xE5`); `OTA_NEED_CRC 1` (so the device always requests a trailing CRC-32); `OTA_MTU_LEN` = **128 on BLE, 512 on SPP** — this caps the device's own notification size, not the 512-byte firmware block it pulls.

**Per-opcode behaviour** (device side):
- `0xE1 GET_FILE_INFO_OFFSET` (lines 618–631): replies `offset=0, len=sizeof(ota_file_header_t)=18` — i.e. "send me the 18-byte wrapper header."
- `0xE2 INQUIRY_IF_CAN_UPDATE` (lines 633–677): the app sends those 18 header bytes; the device checks `vid/pid` against `OTA_VID/OTA_PID` → `result=0x02` on mismatch, else `result=0x03`. **It takes the whole-file length and CRC-32 straight from the wrapper header's `len`/`crc` fields** and stores them (`ota_file_len`, `ota_file_crc`) to verify at the end; a matching len+crc sets `ota_resume_flag` for resume. (This is why `ota_repack.py` must set the wrapper `len`/`crc` correctly.)
- `0xE3 ENTER_UPDATE_MODE` (lines 679–694, 728–779): reply gives `offset = ota_file_offset + 18`, `len = OTA_BLOCK_LEN (512)`, `need_crc = 1`; starts/resumes the flash `ota_task`.
- `0xE5 SEND_FIRMWARE_BLOCK` (cmd `firmware_block_cmd_param_t` = `SN`, `offset(4 BE)`, `data[]`, lines 253–257, 696–726, 809–871): the device computes `getcrc32(data)` and compares it to the trailing 4-byte **big-endian** CRC-32 (`STATUS`/log on mismatch, block dropped); the `offset` is absolute into the file (device subtracts the 18-byte header), data is written via `ota_task_write_ext`, and the reply hands back the next `(offset+18, block_len, delay_ms)`. `block_len=0, offset=0` signals completion; `delay_ms` becomes `1000` while SCO/A2DP is streaming (lines 702–704). A repeated `SN` is ignored (de-dup, lines 841–848).
- `0xE6 GET_REFRESH_FIRMWARE_STATUS` (lines 873+): post-transfer status/commit.
- `0x03 REBOOT` (`reboot_cmd_param_t` type `0`=reboot `1`=shutdown, lines 198–206).

The device also advertises as name **`wq-ota`** with its VID in the manufacturer field when in the OTA/DFU state (`wq_adv_data_t`, lines 298–351) — a recognisable signature if we ever sniff a real update.

## App-side upgrade state machine (`org.wuqi.android.sdk.upgrade`)

Source only, from the decompiled QCY app `work/qcy-app-4.0.7-jadx/sources/org/wuqi/android/sdk/upgrade/`. The BLE transport is `UpgradeModeBle` (writes to the BLE channel via `BluetoothModeBle.write`; `UpgradeModeSpp` is the SPP sibling). The flow is a linear state machine (each state's `setState(new …)` gives the successor):

```
AttachDeviceInformationState   (0x02 device info: battery, TWS, isLeft, isDual)
      → OffsetOTAState         (0xE1 get file-info offset)
      → CanUpdateOTAState      (0xE2 can-update? → single vs double backup)
          ├─ AskEnterUpgradeOTAState → DoubleOsOTAState   (0xE3 enter, 0xE5 data pump; dual-OS path)
          └─ SingleOsOTAState                              (single-OS path)
      → AskUpdateFinishState    (0xE6 refresh status)
          ├─ SyncDeviceState    (0xE8 sync, dual TWS)
          ├─ ChangeDeviceState  (0xE7 role switch, flash the other bud)
          └─ RestartState       (0x03 reboot / commit)
```

`UpgradeOTADefine` (same package) carries only the UI message codes (`MESSAGE_UPGRADE_PROGRESS 100012`, `…_FINISH_SUCCESS 100000`, `…_FINISH_FAIL -100000`, etc.), not the wire opcodes — those live in the device-side enum above. The shipping QCY app drives this over **SPP `0x7034`**, not BLE; the `UpgradeModeBle` class exists but the app does not exercise it (see the channel note at the top of this file).

The only Wuqi command that neither writes flash nor enters update mode. The SDK sends it ~1 s after connect, outside any OTA state.

- Write to the OTA channel: `70 07 6E C0 02 00 05 00 FF FF FF FF 33` (SN forced to 0).
- Reply: `70 07 6E 00 02 <len2> 00 <sn> { L TYPE VALUE[L-1] }* 33` (TLV list; each L counts the TYPE byte).

| TYPE | Value |
|---|---|
| 0 | firmware version: one or two u16 BE (UI labels "Master" / "Minor" — probably primary/secondary bud) |
| 1 | VID (2) + PID (2) |
| 2 | battery L, battery R (percent, one byte each) |
| 3 | TWS connected (1) |
| 4 | isLeft (1) |
| 5 | isDual / synced-TWS upgrade (1) |

This is in principle a read-only way to get the firmware version over 7033. **But it still means writing to service 7033, which our rules forbid** — only attempt it with a saved original state, explicit intent, and read-back, and never the `0xE3/0xE5/0xE7/0x03` opcodes.

## CLI channel (1001/1002) — avoid

Wuqi factory command line. Defined in the SDK but **never called by the QCY app**. Framing and the full command catalog (67 commands, internal user events, the N70's AT-command parser) are in [factory_cli.md](factory_cli.md). It includes read-only queries but also arbitrary memory/flash writes, OEM-MAC overwrite, SOFT_RST, raw HCI and ENTER_DUT/FACTORY/OTA modes. Treat as dangerous; do not probe.
