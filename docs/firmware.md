# Firmware

## The file

| | |
|---|---|
| URL | `http://img.qcymall.com/HT18-MP-V3.0.13-OTA.bin` (plain HTTP, QCY CDN) |
| Version | 3.0.13 (matches the version OpenQCY reported on their unit) |
| versionName | `HT18` → **confirms the N70's QCY-internal model is HT18** |
| modelId | 23877 = `0x5D45` (same as the advertisement vendor ID) |
| Size | 1 042 907 bytes |
| SHA-256 | `ecbc6911c6e5dca68221d4eab8a69dfb230d5235535c43fe4ef5b50b40efa593` |
| remarks | "1. Fix known bugs" |
| Stored | `work/firmware-ht18-3.0.13/` (gitignored, not executed) |

Downloaded 2026-11-10. Source only (not flashed / not verified on the device).

## How to obtain the firmware URL

The QCY app looks up the firmware over its HTTP API, not over Bluetooth. No personal account is needed: the app has a guest ("tourist") mode whose response already contains a usable bearer token.

1. Guest token (no account):
   ```
   GET https://appcontent.qcy.com/user/touristMode
   headers: lang, country, sys_: android, app_version: 4.0.7_720
   → data.token   (form "<userId>_<JWT>")
   ```
2. Firmware lookup:
   ```
   POST https://appcontent.qcy.com/earphoneoOta/findEarphoneoOta
   Authorization: Bearer <token>
   body: {"firmwareVersion":"1.0.0","modelId":23877}
   → data.firmwareUrl, data.currentVersion, data.versionName, data.remarks
   ```
   `modelId` is the advertisement vendor ID (0x5D45 = 23877). A low `firmwareVersion` makes the server return the latest build. The app's own guard only skips the call when the current version is already ≤ `0.0.0.1` (`HTTPApi.checkNewVersion2`).

The endpoint is unauthenticated in practice (any guest token works) and returns a plain-HTTP download link.

## Structure

- **Fully encrypted payload.** Whole-file entropy is 8.000 bits/byte; the body from ~offset `0x90` to the end has maximum entropy with no plaintext anywhere (no strings, no low-entropy windows). Code/strings cannot be recovered without the on-chip key.
- **Plaintext header**, roughly the first `0x90` bytes (entropy ~3.7). It carries a marker `AB CD` (at offset `0x14`, dword `0x0001ABCD`; a second `ABC4` at `0x30`) and a table of little-endian 32-bit values that look like load-address / size descriptors — consistent with a multi-segment image the chip reads by absolute offset during OTA (see [ota.md](ota.md)). Exact field meanings are unknown without Wuqi documentation.
- This matches the device-side OTA error strings "Encryption key mismatch" and "Uboot mismatch": the image is validated and decrypted on the chip, not in the app.

## What this does and doesn't give us

- ✅ Confirmed: internal model HT18, current firmware 3.0.13, the download channel, modelId/vendorId 0x5D45.
- ❌ Not possible from this file alone: reading the firmware code, the chip's exact identity from strings, or extracting keys. The app never decrypts it; the chip does.
