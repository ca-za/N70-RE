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

## Official QCY app and server

| Source | Contents | N70? |
|---|---|---|
| QCY app `com.qcymall.googleearphonesetup` 4.0.7 (720) | decompiled with jadx (`work/qcy-app-4.0.7-jadx/`, not in repo). Generic A001 library `com/qcymall/qcylibrary/`, Wuqi OTA SDK `org/wuqi/android/`, HTTP API `utils/HTTPApi.java`. Pulled from the test phone via ADB. | **yes** (generic, no N70-specific code) |
| QCY OTA server `appcontent.qcy.com` | `user/touristMode` (guest token), `earphoneoOta/findEarphoneoOta` (firmware lookup by modelId). Confirmed N70 = modelId 23877, versionName HT18, FW 3.0.13. | **yes** |
| QCY panel server `api.watch.qcy.com` | `product/findControlPanels` (modelId 23877, firmwareVersion) → the N70's own feature/command panel. Saved as `data/controlpanel_n70.json`, documented in [controlpanel.md](controlpanel.md). | **yes, model-specific** |
| QCY CDN `img.qcymall.com` | firmware image `HT18-MP-V3.0.13-OTA.bin` (encrypted). See [firmware.md](firmware.md). | **yes** |

## Chip

- [WQ7033 overview (PDF)](https://www.wuqi-micro.com/Public/Uploads/uploadfile2/files/20230830/WQ7033EN.pdf)
- [WQ7033 datasheet, Chinese (PDF)](https://www.wuqi-micro.com/Public/Uploads/uploadfile/files/20230830/WQ7033.pdf)
- [WQ7033 product page](https://www.wuqi-micro.com/en/product-center/smart-audio-chip/4)
- [WQ7033AX (wuqi-tech)](http://en.wuqi-tech.com/product/12.html)
- [Wuqi downloads](https://www.wuqi-micro.com/en/service-support/product-data-book/download2)

### WQ7033 community notes (CSDN, Chinese; block automated fetch, read in a browser)

- [WQ7033 OTA firmware update](https://blog.csdn.net/ccdehuiji/article/details/131578652) – OTA package is compressed, can roll back; built from a `.wpk` in the Wuqi UI tool by selecting image regions; OTA code in `app_wqota.c`; opcodes `OPCODE_OTA_GET_DEVICE_INFO / GET_FILE_INFO_OFFSET / INQUIRY_IF_CAN_UPDAT` (match our 0x02/0xE1/0xE2).
- [WQ7033 SDK structure and boot flow](https://blog.csdn.net/ccdehuiji/article/details/131193478) – SDK dirs app/config/driver/os(FreeRTOS)/project; build output `.wpk` (community renames to `.rar` → contains `app_evt.xml`, `audmap_config.json`).
- [WQ7033 app communication](https://blog.csdn.net/ccdehuiji/article/details/131472363), [dev guide](https://blog.csdn.net/dop102/article/details/122359296), [flashing + UI tool / .wpk](https://blog.csdn.net/ccdehuiji/article/details/131208244), [single-wire burn](https://blog.csdn.net/dop102/article/details/123751959).
- Tools named in those blogs: the Wuqi **UI/packaging tool** (imports `.wpk`, exports the OTA `.bin` – the step that encrypts) and the production flasher **`Wuqi.Beetle.Burn.exe`** (single-wire UART, BOOT→VDD). SDK version seen: `sdk_tws_6.1.0.295` (scons build).
- Unofficial mirrors exist of the burn/UI tool ([gitcode 5cec4](https://gitcode.com/open-source-toolkit/5cec4)) and of the "WQ7034-WQ7033 native SDK source" (CSDN "free share", 2025) – almost certainly **unauthorised redistribution of proprietary NDA software, unverified, Windows binaries**. Not downloaded.

**Decryption research conclusion (2026-11-10):** No public firmware key, decryptor, `.wpk` unpacker, or firmware dump exists for WQ7033 on GitHub, CSDN, GitCode, 4PDA or RuTracker. The ecosystem (SDK, OTA source `app_wqota.c`, packaging/flash tools) is real but **NDA-only**; the only public copies are unauthorised leaks. The one static lever that could reveal the cipher/key would be the leaked SDK + packaging tool, read-only – see [ideas.md](ideas.md).

## Contradictions between the sources

| Topic | Source A | Source B | Observed on the N70 |
|---|---|---|---|
| Internal model | README guesses "probably HT18" | OTA server `versionName` = HT18 | **HT18** ✅ confirmed |
| ANC opcode | HT07: `0x0C` (1 byte, scene<<4\|level) | OpenQCY/qcyx: `0x17` (3 bytes) | `0x17` ✅ |
| Prompt volume `0x1D` | OpenQCY: 1 byte | qcyx: 2 bytes `<lvl> 00` | **only 2 bytes work** ✅ |
| `0x1D` reply byte 2 | qcyx: status | OpenQCY: maximum | constant `0F`, consistent with max 15 |
| Custom EQ byte 0 | OpenQCY: 8 | Quicky: 2 | keeping the factory 0x81 works |
| Custom EQ band format | OpenQCY/Quicky v2: freq,gain,Q,type | qcyx HT08: `[00, marker, freq, gain, 64]` | OpenQCY format ✅ |
| `0x1F` | qcyx: auto power-off u16 | Quicky: standby 1 byte | 2 bytes in the blob |
| ANC_RESULT `0x28` | qcyx: HT08 only | – | also sent by the N70 ✅ |
