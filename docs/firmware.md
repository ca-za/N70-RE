# Firmware

## Headline: the firmware is NOT encrypted – it is LZMA-compressed

Earlier we assumed the OTA image was encrypted (entropy 8.0). It is not. Using the public WuQi SDK source (see [sources.md](sources.md)) we learned the exact package format, parsed the image, and both CRC-32s check out. Each image block is a standard **`.lzma` (LZMA_ALONE)** stream. All six images decompress to exactly the sizes the header states. No key, no cipher. Extractor: [`tools/ota_unpack.py`](../tools/ota_unpack.py).

The decompressed firmware is readable (RISC-V code, DSP libs, the QCY app, strings), which also **corrects the chip identity**: build tag `QCY_HT18-7035AX-B-ADK_1.3.6.27-LDAC-20251219`, code prints `WQ7036` → the N70 uses a **WQ703X (7035AX / 7036)**, not the WQ7033 we had guessed. See [hardware.md](hardware.md).

## The file

| | |
|---|---|
| URL | `http://img.qcymall.com/HT18-MP-V3.0.13-OTA.bin` (plain HTTP, QCY CDN) |
| Version | 3.0.13 (firmware string `FW-VERSION-v0.3.0.13`) |
| versionName | `HT18` → the N70's QCY-internal model |
| modelId | 23877 = `0x5D45` (advertisement vendor ID) |
| Size | 1 042 907 bytes |
| SHA-256 | `ecbc6911c6e5dca68221d4eab8a69dfb230d5235535c43fe4ef5b50b40efa593` |
| ADK | `wq-adk` 1.3.6.27, build 2025-12-19, project path `/root/projects/HT18/wq-adk/` |
| Stored | `work/firmware-ht18-3.0.13/` (gitignored, not executed) |

Downloaded 2026-11-10. Source only (not flashed / not verified on the device).

## How to obtain the firmware URL

Over the QCY HTTP API, no personal account needed (guest token):
1. `GET https://appcontent.qcy.com/user/touristMode` (headers `lang`, `country`, `sys_: android`, `app_version: 4.0.7_720`) → `data.token`.
2. `POST https://appcontent.qcy.com/earphoneoOta/findEarphoneoOta`, `Authorization: Bearer <token>`, body `{"firmwareVersion":"1.0.0","modelId":23877}` → `data.firmwareUrl`, `currentVersion`, `versionName`.

A low `firmwareVersion` makes the server return the latest build.

## Package format

All little-endian unless noted. Confirmed by parsing: both CRCs match, all blocks decompress to the stated sizes.

```
ota_file_header_t   18 bytes, big-endian fields (QCY's transfer wrapper):
    vid(2) pid(2) version(2) len(4) reserved(4) crc(4)
    (our file: len = filesize-18; the SDK default is vid=0x076E pid=0x7033)
pack_desc_t         16 bytes:
    magic(4) = 0xABCD6543   fw_version(4)   image_pack_types(4)   time_stamp(4)
image_desc[N]       16 bytes each, N = popcount(image_pack_types):
    image_size(4)  image_compress_size(4)  image_start_addr(4)  image_end_addr(4)
header_crc(4)       CRC-32 over the image_desc[] array
<compressed blocks> each image's .lzma stream, concatenated
data_crc(4)         CRC-32 over all the compressed blocks
```

The N70 image: `pack_types=0x3F` → 6 images.

| # | start addr | compressed | raw | content (from strings) |
|---|---|---|---|---|
| 0 | `0x00000002` | 144 | 304 | boot/descriptor (low entropy) |
| 1 | `0x00010000` | 269 860 | 502 724 | **core0** firmware (RISC-V, QCY app `qcy_app.c`, BT host) |
| 2 | `0x000AB000` | 384 260 | 614 432 | **core1** firmware |
| 3 | `0x00169000` | 386 144 | 702 128 | **DSP** firmware (wq aec/drc/eq/ldac/sbc/asrc libs) |
| 4 | `0x003EE000` | 880 | 7 180 | config |
| 5 | `0x003F0000` | 1 481 | 3 768 | tone / prompts |

CRC-32 is standard zlib. Magic, struct and the no-encryption/compression design come from the device-side OTA code in the public SDK (`ota.h`, `ota.c`, `app_wqota.c`). Note: the app's status strings "encryption key mismatch" / "uboot mismatch" are generic OTA result labels, not evidence that this image is encrypted.

## Extracting it

```
python3 -I tools/ota_unpack.py work/firmware-ht18-3.0.13/HT18-MP-V3.0.13-OTA.bin work/firmware-ht18-3.0.13/extracted
```
Verifies both CRCs and writes the six decompressed images. The raw images are RISC-V firmware and can be loaded into Ghidra/radare2 (RISC-V, little-endian) at their `image_start_addr`.

## What this gives us

- ✅ Full, decompressed firmware for all cores – no decryption needed.
- ✅ Confirmed: chip WQ703X (7035AX/7036), FW 3.0.13, ADK 1.3.6.27, internal model HT18.
- Open: full disassembly/analysis of the RISC-V images (load addresses known); extracting keys for *other* things (e.g. the BLE pairing) would be separate work.
