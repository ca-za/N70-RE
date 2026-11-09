# GATT (Bluetooth LE)

All services of the peripheral `QCY MeloBuds N70-APP` (via `discoverServices(nil)`):

`7033`, `A001`, `180A`, `FE2C`

No LE Audio services (PACS 1850, ASCS 184E, BASS 184F, CAS 1853, TMAS 1855, VCS 1844, MICS 184D).

## A001 – QCY control service

| Char | Properties (raw) | Meaning |
|---|---|---|
| `1001` | 4 = write without response | commands to the device |
| `1002` | 18 = read + notify | replies; a **read** returns the complete settings blob (see protocol.md) |
| `0008` | 18 = read + notify | battery `[L, R, Case]`, bit 7 = charging, bits 0–6 = percent. Notifies about every 10 s / on change |

**On this N70 only 1001, 1002, 0008 were found** (discovery used the filter `[1001, 1002, 0008]` – the others were not explicitly searched for, still open!).

The QCY app 4.0.7 (`ControlerPanl.java`, `QCYHeadsetClient.java`) defines more A001 characteristics for the generic client; the N70 may expose some of them (needs a full `discoverCharacteristics(nil)` to confirm):

| Char | Use (app) |
|---|---|
| `0007` | firmware version, read: 6 bytes `L a.b.c` + `R a.b.c` |
| `0008` | battery L/R/case (confirmed above) |
| `0009` | prompt-language string (comma-separated, first = current) |
| `000A` | legacy reset: 01 reset / 02 clear pairing / 03 factory ⚠ |
| `000B` | legacy 10-band EQ |
| `000C` | time sync (v1) |
| `000D` | key remap v2 (raw `[keyId, funcId]` pairs, see protocol.md) |
| `000E` | ZR settings |
| `000F` | function v1 (byte 0 = in-ear check); read on connect |

Max write length: 509 bytes (without response) / 512 (with response) → the 147-byte EQ frame fits.

## 7033 – probably the Wuqi chip service (OTA/debug)

| Char | Properties |
|---|---|
| `1001` | write without response |
| `1002` | notify |
| `2001` | write without response |
| `2002` | notify |

Nothing readable. Two command/reply pairs – typical for OTA (control channel + data channel). **Do not write.** Note: same 16-bit IDs `1001`/`1002` as in A001 – always select characteristics together with their service.

Confirmed by the app's Wuqi SDK (`org/wuqi/android/core/base/UUIDValue.java`): `2001`/`2002` = OTA write/notify, `1001`/`1002` = Wuqi factory **CLI** write/notify (a different protocol from A001's 1001/1002). The app flashes WQ firmware over classic Bluetooth SPP (`7034`), not over this BLE service. Framing, state machine and the one read-only query (`0x02` device info) are in [ota.md](ota.md). The CLI channel includes FORCE_CRASH / SOFT_RST / SET_KV – treat all of 7033 as dangerous.

## 180A – Device Information

Contains only `2A26` Firmware Revision = `0.0.0.0` (placeholder). No manufacturer, model or serial number.

## FE2C – Google Fast Pair

Service data seen in advertisements of other devices (`FE2C=00505052...`). For quick pairing on Android.
