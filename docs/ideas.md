# Open questions and next steps

## Low risk

1. **Decompile the QCY Android app** (jadx) – read only, never run it
   - complete command table for HT18/N70, hidden settings
   - what the app sends over service 7033 (OTA flow, frame format)
   - whether firmware files ship in the APK or are downloaded from a server (URL, format, signature)
   - prefer the official source (Play Store); otherwise a mirror, unpacked into its own empty folder
2. **Bluetooth capture** of the QCY app on an Android phone (developer options → "Bluetooth HCI snoop log"), then analyze with Wireshark. Shows real command sequences incl. EQ presets and the update flow.
3. **Look for characteristics `0007` (firmware version) and `000D` (touch mapping)** (discovery without filter) and read them – read only.
4. **Unknown fields** in the settings blob (`04`, `48`, `19`) and in the advertisements (index 4–6, 10–12, 19): map them by observing state changes.
5. **EQ:** confirm type code 3 (shelf?) with a listening test; check the effect of the master gain; only read other preset IDs, don't write them until the app analysis confirms them.

## High risk / big effort

6. **Get the firmware** (from the app download or an update capture), analyze its structure (RISC-V, possibly encrypted/signed).
7. **Custom firmware** – e.g. enable LE Audio (the chip supports BLE Audio according to the datasheet). Without SDK/docs: weeks to months, **risk of bricking** when flashing over 7033. Only with a spare unit.

## Don't

- Try unknown opcodes (could trigger a factory reset, delete pairings, etc.)
- Send anything to service 7033 as long as the OTA flow isn't understood
- LED control: no command known, the earbuds probably only have a case LED under firmware control

## Related

- LDAC from a Mac: macOS only does SBC/AAC; a custom A2DP/AVDTP implementation over IOBluetooth L2CAP might work (unverified)
- LE Audio: the Mac supports it (`LEA`), the N70 offers no LE Audio services
