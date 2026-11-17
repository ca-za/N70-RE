# Custom firmware — feasibility, flashing routes, roadmap

Working document for the goal: **reverse-engineer the platform far enough to build, flash and freely modify our own firmware** on the N70, at the binary level (we will not get the original NDA source; see [dev_platform.md](dev_platform.md)). Scope chosen: **custom features / custom firmware**, on a **spare/sacrificial unit**, **recovery net first**.

## 1. Headline: no secure boot, no image signing ✅

Image integrity on the N70 is **guard magic + CRC-32 only** — there is **no signature, no secure boot, no encryption**. Evidence (all from the decompressed firmware + the structurally-identical public ADK `work/zt210-sdk/`):

| Stage | What it checks | Source |
|---|---|---|
| **Boot loader** (loads each core) | `img_hdr->guard == 0xA4E49A17` only; else "BT image is bad" | `core0/src/lib/loader/src/iot_loader.c` |
| **OTA receive/apply** | magic `0xABCD6543` + CRC-32 of `image_desc[]` + CRC-32 of the compressed blob | `core0/src/lib/ota/src/ota.c:ota_image_verify()` |
| **Per-image header** | `iot_flash_image_header_t` = guard, length, version, start, **crc**, `tlv_count`, reserved | `core0/src/driver/non_os/boot_map/iot_boot_map.h` |
| **Our real N70 images** | every image has `tlv_count = 0` → no appended signature TLV | `tools/ota_unpack.py` dump |
| **Whole SDK** | no `secure_boot` / `rsa` / `ecdsa` / `ed25519` / `signature` (the only grep hits are FreeRTOS comments) | grep over `work/zt210-sdk/` |

The clincher: the shipping firmware is itself **unsigned** (`tlv_count=0`) and it boots. Even if the silicon supports efuse secure boot, QCY did not enable it on this product.

**Consequence:** a modified image with correctly recomputed CRC-32s will be accepted and booted. We do **not** strictly need hardware flashing to run custom code — the OTA-over-BLE path is viable. Hardware (UART) remains our recovery net.

> Caveat still to confirm: the **first-stage boot ROM / SBL** (`BOOT_SECTION_SBL 0xFE`) is on-chip mask ROM, not in the OTA image, so we cannot read it from the image. But since the on-flash images are unsigned and boot, any ROM-level check is not enforcing signatures on this product. We will confirm directly once we can read the live flash over UART (Phase 1).

## 2. Two flashing routes

**Route 1 — OTA over BLE (no soldering).** Repack a modified image (fix CRC-32s) and push it via service 7033 (OTA, chars 2001/2002). The receive path only checks magic + CRC. This is the "free modification" path. It is forbidden by the default CLAUDE.md rule; the user has authorised lifting that rule **for the spare unit only**.

**Route 2 — single-wire UART (test pads).** The chip flashes/reads over single-wire UART (`Wuqi.Beetle.Burn.exe`, BOOT→VDD, pogo/test pads). This is the **recovery net**: read back stock flash, un-brick, dump the SBL/boot ROM and the real flash layout, and capture live debug logs. Needed because Route 1 can brick.

Constraint: **no Windows PC available**, so `Wuqi.Beetle.Burn.exe` is out (barring Wine). Plan: **reverse the single-wire burn protocol from the SDK and build our own flasher in Python** driving the user's 3.3 V USB-UART adapter. Fits the "custom everything" goal and avoids the vendor tool. (No logic analyzer either; not on the critical path — the UART adapter both flashes single-wire and reads debug logs.)

## 3. Roadmap

### Phase 0 — static, no hardware (in progress)
- [x] Confirm no secure boot / no signing (above).
- [x] **Repack tool** [`tools/ota_repack.py`](../tools/ota_repack.py): inverse of `ota_unpack.py`. Takes modified raw images → recomputes each per-image `iot_flash_image_header_t.crc` (CRC-32 over the code bytes after the 32-byte header, length = `header.length`; confirmed against all five stock guarded images) → LZMA-compresses (`FORMAT_ALONE`) → rebuilds `image_desc[]` → header CRC-32 → concat blocks → data CRC-32 → wraps `ota_file_header_t` (18 B, big-endian, `len` + CRC-32). `--selftest` proves the semantic round-trip: unpack→repack→unpack gives valid CRCs and byte-identical decompressed images. (Whole-file byte-identity with the stock `.bin` does **not** hold and is not needed — Python's LZMA encoder differs from WuQi's; the device checks only guard-magic + CRC-32.)
- [ ] Map the **7033 OTA transport** precisely (chars 2001/2002, chunking, acks, the `OPCODE_OTA_*` state machine) from `app_wqota.c` + `ota_transport_ble.c` + the app. Best cross-check: a **BT HCI snoop log of a real OTA update** from the Android app (user can capture).
- [ ] Continue disassembly of `qcy_app` (app core) to locate feature code worth changing.

### Phase 1 — recovery net (needs the spare unit + UART)
- [ ] Open the spare, locate the earbud **UART/BOOT test pads** (microscope).
- [ ] Reverse the single-wire burn protocol; build `tools/wq_flash.py`.
- [ ] **Read back the live flash** (proves the flasher + gives SBL/boot ROM + real partition/boot map + calibration). This is the un-brick capability; nothing gets flashed until this works.

### Phase 2 — first modified boot
- [ ] Trivial benign change (e.g. a string / tone), repack, **flash via UART first** (we control recovery), confirm it boots.
- [ ] Then flash the same via **OTA/7033** to validate the no-solder path end to end.

### Phase 3 — real custom features
- [ ] Patch `qcy_app` / BT core for the desired behaviour (binary patching; keep CRCs valid). Candidates: unlock source-only opcodes, change defaults, new control behaviour. (LE Audio stays out of reach — needs LC3/ISO/BAP that aren't in the build; see [firmware_internals.md](firmware_internals.md).)

## 4. What we need from the user

- **A spare/sacrificial N70** (ideally two) — the one gating item for Phases 1–2. *To procure.*
- Already have: 3.3 V USB-UART adapter, soldering + microscope. *Sufficient for Phase 1.*
- Nice to have: a **BT HCI snoop log of a real OTA update** (Android developer options) — sharpens the Phase-0 7033 mapping.
- Not available (worked around): logic analyzer (defer), Windows PC (we build our own flasher instead of the vendor tool).

## 5. Risks

- Route 1 OTA write to 7033 can brick → only on the spare, only after Phase 1 recovery works.
- Modifying code shifts nothing in layout if we patch in place and keep sizes; adding code needs free space / relocation — handle later.
- Keep the stock OTA `.bin` and a full flash read-back as golden images for restore.
