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
| Firmware | 3.0.13 (confirmed: the OTA server returns this as the current build for modelId 23877; the image is archived and **unpacked** — LZMA-compressed, not encrypted, see [firmware.md](firmware.md)); the Device Information service only reports `0.0.0.0` |
| Model string | `WQ00` (ASCII in settings field 0x19) |

## Chip: Wuqi WQ703X (WQ7035AX / WQ7036) ✅

Confirmed from the decompressed firmware ([firmware.md](firmware.md)): the build tag is `QCY_HT18-7035AX-B-ADK_1.3.6.27-LDAC-20251219` and the code prints `WQ7036`. So the N70's chip is a **WQ703X, specifically 7035AX (code references 7036)** — **not** the WQ7033 we had guessed (the `7033` is only the GATT service UUID / SDK family name, not the die). Same WuQi ADK family; the datasheet facts below (dual RISC-V, HiFi 5 DSP, NPU, hybrid ANC, BLE Audio) apply to the 703X series.

Earlier supporting evidence: the QCY app classifies a device as Wuqi (`isWQDevice`) when `vendorId & 0xF0 == 0x40`; the N70's `0x5D45` matches, and OTA routes through the Wuqi presenter (`WQPresenterNew`). Model string `WQ00` is the voice-prompt pack, not the chip.

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

## Charging case

The case has **no radio** (no Bluetooth of its own). It talks to the earbuds over the **charging contacts (pogo pins)** using a bit-banged single-wire protocol **modulated onto the charge line**: the case switches the charging voltage on/off in timed pulses, and a bud decodes the bitstream by sampling its charge-detect flag on a timer (8-bit opcodes). Source: the WuQi ADK `vendor/charger_box/charger_box_wq.c` (`battery_charger_get_flag()` polled in a timer, `cur_bit_count`, `sm_param(...,8)`).

**The case has its own controller/MCU** (the "smart" `charger_box_wq` variant — the N70 uses it, since it reports case battery and lid events, which the dumb `charger_box_none` variant cannot). Over the charge line it sends (`charger_box.h` events / `BOX_MSG_OPT_CODE_*`):

| Case action | Opcode / event |
|---|---|
| Lid open / close | `0x50` / `0x51` (`BOX_OPEN`/`BOX_CLOSE`) |
| Case button long-press | `0x52`=3 s, `0x53`=10 s, `0x59`=20 s |
| Enter pairing | `0x57` (`ENTER_PAIR`) |
| Enter DUT / OTA mode | `0x55` / `0x56` |
| Shutdown / reset / reconfig | `0x58` / reset / `0x54` |
| Case battery | `CHARGER_EVT_BOX_BATTERY` → `{battery:7, charging:1}` |

So the case button and lid are what trigger pairing, reset and the connect/popup behaviour, and the case reports its own battery this way (the earbuds then forward it in the BLE advertisement and over Google Fast Pair — `gfps_get_box_battery`).

**Case firmware:** the case MCU runs its **own firmware on a separate chip** — **not** part of the earbud OTA image we unpacked (that is only the three earbud cores). We do not have the case firmware. Per third-party notes the case is flashable over its pogo pins too ("POGO-pin single-line upgrade"), presumably at the factory.
