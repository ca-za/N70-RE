# Sibling device: QCY MeloBuds Pro (HT08)

Not the main target, but a **sibling WuQi device** examined to see how close its architecture is to the N70. Short answer: **same platform family** (WuQi WQ703-series, same A001 + 7033 protocol), one generation older. Marked ✅ confirmed / otherwise inferred.

## Identity ✅

| | |
|---|---|
| Marketing name | QCY MeloBuds Pro (launched Aug 2024) |
| Internal model | **HT08** ✅ (PCB silkscreen, and the A001 version string reads "QCY MeloBuds Pro") |
| modelId / vendor ID | **19786 = `0x4D4A`** ✅ (decoded from the BLE advertisement, big-endian bytes [2–3], same format as the N70's `0x5D45`; validated: `findControlPanels` returns a panel for 19786, not for 19021) |
| Classic BT address | `84:AC:60:22:AD:C0` |
| BLE (control) address | `C4:AC:60:22:AD:C1`, name `QCY MeloBuds Pro-APP` |
| Bluetooth / codecs | BT 5.3; SBC, AAC, **LDAC**; adaptive hybrid ANC (vendor claim 46 dB) |
| Firmware line | ~**1.0.x** (control panel `firmwareversionLte 1.0.5`), vs the N70's 3.0.x |

WuQi membership confirmed two ways: the app's `isWQDevice` rule (`vendorId & 0xF0 == 0x40` → `0x4A & 0xF0 == 0x40` ✓), and the GATT **service 7033** (the WuQi OTA/CLI service) alongside A001.

## Hardware — PCB inspection ✅

From photos of the opened right earbud PCB:

- **Silkscreen `WQ703…`** → the board is a **WuQi WQ703-series** design — the same chip family as the N70 (whose firmware reports `7035AX`). The exact die variant (e.g. 7033 vs 7035) is the board-family name only, not legible here; the main SoC is under a shield / on the other side and could not be exposed without destroying the board.
- Silkscreen `HT08`, channel markings `R` / `RX`.
- **16.0000 MHz** crystal (SoC reference clock).
- A MEMS microphone (metal can, marking `R468 / 22XX`) and an optical in-ear/wear-detection sensor.

Being BT 5.3 (vs the N70's BT 6.1 / WQ7035AX), the Pro is most likely an **earlier WQ703x variant** — consistent with the genuine WQ7033-class part (the WQ7033 datasheet lists BT 5.3). Not firmware-confirmed (see below).

## Protocol — same as the N70 ✅

Same control service **A001** (write 1001 / notify 1002) and the same collision with **service 7033** (documented independently by the qcyx project for the HT08). The N70's control-panel-derived opcodes carry over; from the Pro's own server control panel (`data/controlpanel_pro_ht08.json`, modelId 19786):

- Feature opcodes shared with the N70: **`0x14`** timing power-off, **`0x2C`** wear detection, **`0x1F`** disconnect-and-power-off, gaming mode, ANC mode.
- **Identical key-remap function map:** 0 none, 1 play/pause, 2 prev, 3 next, 4 voice assistant, 5 vol+, 6 vol−, 7 gaming, **11 ANC** — exactly the N70's set.

So the A001 command semantics are shared; a controller built for the N70 should largely drive the Pro too (feature set differs per model panel).

## Firmware — not obtainable via the QCY OTA server ✗

`POST appcontent.qcy.com/earphoneoOta/findEarphoneoOta` with `modelId=19786` returns `data: null` (tried `firmwareVersion` 1.0.0 and 0.0.0). QCY has **no OTA image published** for the Pro on the endpoint that served the N70's `HT18-MP-V3.0.13-OTA.bin`. Consequence: we **cannot pull and unpack the Pro firmware** the way we did for the N70, so the exact die variant and the core/memory map stay unconfirmed for this model. (A firmware dump would instead need the physical UART/test-pad route — [custom_firmware.md](custom_firmware.md).)

## Bottom line

The MeloBuds Pro is the **same WuQi WQ703 platform and the same A001/7033 protocol** as the N70, one generation earlier (BT 5.3, firmware 1.0.x). Protocol work transfers directly; firmware-level work does not, because no OTA image is available for it. Sources for the specs: [qcyx HT08 protocol docs](https://github.com/BrunoAssis/qcyx/tree/HEAD/docs/protocol), [audioreviews.org](https://www.audioreviews.org/qcy-melobuds-pro-review/).
