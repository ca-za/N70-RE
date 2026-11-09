# Hardware

## Device

| | |
|---|---|
| Model | QCY MeloBuds N70 (QCY-internal **HT18** ✅ confirmed via the OTA server's `versionName`) |
| modelId / vendor ID | 23877 = `0x5D45` (advertisement + OTA server `modelId`) |
| Advertised | Bluetooth 6.1, ANC (adaptive), LDAC, multipoint |
| Classic BT address | `C4:33:96:02:76:C0` |
| Name (classic) | `QCY MeloBuds N70` |
| Name (BLE, control channel) | `QCY MeloBuds N70-APP` |
| Firmware | 3.0.13 (confirmed: the OTA server returns this as the current build for modelId 23877; the encrypted image is archived, see [firmware.md](firmware.md)); the Device Information service only reports `0.0.0.0` |
| Model string | `WQ00` (ASCII in settings field 0x19) |

## Chip: Wuqi WQ7033 (very likely)

Evidence: vendor-specific BLE service `7033`, model string `WQ00`, QuickyAndroid has a dedicated `WuqiGattClient`. The QCY app 4.0.7 confirms it: it classifies a device as Wuqi (`isWQDevice`) when `vendorId & 0xF0 == 0x40`. The N70's `0x5D45` has low nibble group `0x40`, and the app's OTA routing sends it down the Wuqi presenter (`WQPresenterNew`). The firmware filename `HT18-...-OTA.bin` and the Wuqi SDK's `7033`/`7034` OTA channels tie it to Wuqi. The exact die (WQ7033 vs. a variant) is still not proven – the encrypted firmware contains no readable chip string.

According to the [Wuqi datasheet (overview)](https://www.wuqi-micro.com/Public/Uploads/uploadfile2/files/20230830/WQ7033EN.pdf) / [product page](https://www.wuqi-micro.com/en/product-center/smart-audio-chip/4):

- Dual-mode Bluetooth 5.3 including **BLE Audio** (the hardware could do LE Audio, the firmware doesn't offer it)
- 2× RISC-V CPU, Cadence **HiFi 5 DSP**, NPU
- Hybrid ANC (feedforward + feedback)
- Variant WQ7033AX: BT 5.2, 3× RISC-V, QFN package ([wuqi-tech](http://en.wuqi-tech.com/product/12.html))

Contradiction: Wuqi states BT 5.3, QCY advertises 6.1 – either a newer chip variant or marketing.

**No public SDK.** Download page: [Wuqi Bluetooth audio chips](https://www.wuqi-micro.com/en/service-support/product-data-book/download2) (datasheets only). The SDK is probably only available to device makers under NDA. No open-source or hobbyist projects for the chip were found (as of 2026-11).

## Bluetooth profiles towards the Mac

`system_profiler SPBluetoothDataType`:

- `QCY MeloBuds N70`: `Services: 0x800019 < HFP AVRCP A2DP ACL >` – classic profiles only
- `QCY MeloBuds N70-APP`: `Services: 0x400000 < BLE >` – the control channel
- The Mac itself: `< HFP AVRCP A2DP HID Braille LEA AACP GATT SerialPort >` – the Mac could do LE Audio (`LEA`)

Audio codecs with macOS: SBC, AAC (A2DP); CVSD/mSBC (HFP). macOS can't do LDAC.

## Behavior

- A bud in the case disconnects from the Mac.
- With only one active bud, macOS reports **no** battery level at all; the QCY channel still delivers values (L or R + case).
- BLE advertisements (with battery) only now and then, mainly when opening the case / taking buds out (see advertising.md).
- A BLE control connection can only be established while they advertise. After that it stays up (also when the controlling app restarts, since CoreBluetooth keeps the connection system-wide).
- The first connection attempts were dropped by the device after ~1 s (probably because the buds were in the case at that moment); stable later.
