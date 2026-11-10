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

## Read-only device-info query `0x02`

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
