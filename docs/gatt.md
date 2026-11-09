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

According to OpenQCY, other firmwares also have `0007` (firmware version, read), `000D` (touch mapping, read/write) and `000B` (legacy EQ presets). **On this N70 only 1001, 1002, 0008 were found** (discovery used the filter `[1001, 1002, 0008]` – `0007`/`000D` were not explicitly searched for, still open!).

Max write length: 509 bytes (without response) / 512 (with response) → the 147-byte EQ frame fits.

## 7033 – probably the Wuqi chip service (OTA/debug)

| Char | Properties |
|---|---|
| `1001` | write without response |
| `1002` | notify |
| `2001` | write without response |
| `2002` | notify |

Nothing readable. Two command/reply pairs – typical for OTA (control channel + data channel). **Do not write.** Note: same 16-bit IDs `1001`/`1002` as in A001 – always select characteristics together with their service.

## 180A – Device Information

Contains only `2A26` Firmware Revision = `0.0.0.0` (placeholder). No manufacturer, model or serial number.

## FE2C – Google Fast Pair

Service data seen in advertisements of other devices (`FE2C=00505052...`). For quick pairing on Android.
