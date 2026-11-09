# BLE advertisements

Sent with manufacturer ID **0x521C** (QCY). macOS includes the ID in `kCBAdvDataManufacturerData` (little-endian `1C 52` at the start). Raw data: `data/adverts.txt`.

## Layout (index from the start of the macOS manufacturer data)

```
1c52 | 5d45 | 7d05 | 6e | 62 | 61 | 2e | 4f8a40 | 33c496c07602 | bc | 33c496f88002
 ID    vendor  ?    ?    L    R   case   ?      address 1       ?    address 2
```

| Index | Meaning | Source |
|---|---|---|
| 0–1 | company ID 0x521C | – |
| 2–3 | vendor ID big-endian `5D45` (= 23877, N70; OpenQCY lists 0x5D40/0x5D45) | OpenQCY |
| 4–5 | unclear, changes (`7d05`, `bd45`, `7004`, `4f05`, `7104`, `7804`) | – |
| 6 | flags? `6e` / `4c` – changes with the case state | – |
| **7** | **battery left** (bit 7 = charging) | ✅ compared with the QCY app |
| **8** | **battery right** | ✅ |
| **9** | **battery case** | ✅ |
| 10–12 | unclear | – |
| 13–18 | control address: `33 C4 96 C0 76 02` → `C4:33:96:02:76:C0` (permutation according to OpenQCY: 14,13,15,18,17,16) | OpenQCY |
| 19 | counter? changes (`bc`, `c8`, `c9`, `cd`, `cf`, `d2`, `99`) | – |
| 20–25 | second address, same permutation | OpenQCY |

(OpenQCY counts without the 2-byte company ID: battery there at 5/6/7.)

Battery confirmation: advertisement `62 61 2E` = L 98 %, R 97 %, case 46 % – confirmed by the QCY app.

## When are they sent?

- When opening the case / taking buds out / putting them back, for a few seconds (Android popup)
- **Not** while the buds are simply being worn
- While advertising, the device is connectable (`isConnectable = true`); only then can a BLE control connection be established
- A pending `connect()` (CoreBluetooth keeps it open) connects automatically on the next advertisement
