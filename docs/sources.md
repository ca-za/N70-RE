# Sources

## Protocol

| Project | Contents | N70? |
|---|---|---|
| [GiorgioRafael/OpenQCY-Desktop](https://github.com/GiorgioRafael/OpenQCY-Desktop) | Windows controller; `docs/protocol-research.md`, `Protocol/QcyCommands.cs`, `QcyPacket.cs`, `QcyUuids.cs`, `QcyAdvertisement.cs`, `Device/QcyDeviceClient.cs` | **yes**, validated on hardware (FW L/R 3.0.13) |
| [hui1601/QuickyAndroid](https://github.com/hui1601/QuickyAndroid) | Android app, 40+ commands; `ble/Protocol.kt`, `ble/QcyGattClient.kt`, `WuqiGattClient`, `JlGattClient`, `ZrGattClient` | HT18 according to its README |
| [BrunoAssis/qcyx](https://github.com/BrunoAssis/qcyx) | desktop app; `docs/protocol/` (anc.md, eq.md, device-settings.md, packet-reference.md, ble-device.md) | MeloBuds Pro (HT08), N70 "planned" |
| [Tekkiech/qcy-ht07-protocol](https://github.com/Tekkiech/qcy-ht07-protocol) | protocol report HT07 (Arcbuds), command table | HT07 |
| [Tekkiech/ht07menu](https://github.com/Tekkiech/ht07menu) | macOS menu bar app for HT07 | HT07 |
| [Matheus-TestUser1/OpenQCY](https://github.com/Matheus-TestUser1/OpenQCY) | Flutter app (MeloBuds Pro) | – |
| [jean-vr/oqcy](https://github.com/jean-vr/oqcy) | Expo app, HT05 | – |
| [mtahmid20/QCY-Arcbuds-Controller](https://github.com/mtahmid20/QCY-Arcbuds-Controller) | Arcbuds | – |

## Chip

- [WQ7033 overview (PDF)](https://www.wuqi-micro.com/Public/Uploads/uploadfile2/files/20230830/WQ7033EN.pdf)
- [WQ7033 product page](https://www.wuqi-micro.com/en/product-center/smart-audio-chip/4)
- [WQ7033AX (wuqi-tech)](http://en.wuqi-tech.com/product/12.html)
- [Wuqi downloads](https://www.wuqi-micro.com/en/service-support/product-data-book/download2)

## Contradictions between the sources

| Topic | Source A | Source B | Observed on the N70 |
|---|---|---|---|
| ANC opcode | HT07: `0x0C` (1 byte, scene<<4\|level) | OpenQCY/qcyx: `0x17` (3 bytes) | `0x17` ✅ |
| Prompt volume `0x1D` | OpenQCY: 1 byte | qcyx: 2 bytes `<lvl> 00` | **only 2 bytes work** ✅ |
| `0x1D` reply byte 2 | qcyx: status | OpenQCY: maximum | constant `0F`, consistent with max 15 |
| Custom EQ byte 0 | OpenQCY: 8 | Quicky: 2 | keeping the factory 0x81 works |
| Custom EQ band format | OpenQCY/Quicky v2: freq,gain,Q,type | qcyx HT08: `[00, marker, freq, gain, 64]` | OpenQCY format ✅ |
| `0x1F` | qcyx: auto power-off u16 | Quicky: standby 1 byte | 2 bytes in the blob |
| ANC_RESULT `0x28` | qcyx: HT08 only | – | also sent by the N70 ✅ |
