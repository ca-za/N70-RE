# Tone / audio prompts — where they live and whether we can swap them

Goal of this note: the user wants to **replace the earbuds' prompt sounds** ("swap the
sounds"). This is a static (offline) investigation of the decompressed OTA image
([firmware.md](firmware.md), [firmware_internals.md](firmware_internals.md)) plus the
public WuQi ADK source (`work/zt210-sdk/`, the `qqq5127/ZT210` tree, see
[sources.md](sources.md)). Nothing here was read from or written to a device.

**Short answer:** the N70 has exactly **one** small tone partition (flash `0x3F0000`,
8 KB sector, 3736 bytes used). It ships **inside the OTA image** (pack image #5), so at
the *partition* level it is reachable with `ota_unpack` → edit → `ota_repack`, and there
is no secure boot / signing to stop that ([custom_firmware.md](custom_firmware.md)).
But the blob's **internal container format is not the documented WuQi tone layout and is
not cleanly decoded**, so we cannot yet author a valid replacement clip that the firmware
will play. There is **no separate multilingual voice-prompt partition** anywhere in the
~4 MB flash — the "WQ00/WQ01/WQ02/WQ03 language packs" do not exist on this product as
audio. Details and evidence below.

## 1. The full flash partition map ✅ (from the OTA boot map, img0)

`img0_bootmap_0x00000002.bin` (the OTA's image #0) is an array of 20-byte
`iot_boot_map_image_t` records (`work/zt210-sdk/.../boot_map/iot_boot_map.h`:
`image_type(1) reserved(3) code_lma(4) code_vma(4) code_length(4) code_area_size(4)`).
Parsed in full:

| type | flash LMA | run addr (VMA) | used length | max (area) | role |
|---|---|---|---|---|---|
| `0x10` SBL0 | `0x000000` | `0x02050000` | — | `0x10000` | secondary boot loader (not in OTA) |
| `0x30` C1FW0 | `0x010000` | `0xB4010020` | `0x7ABA4` | `0x9B000` | **BT core** (OTA img1) |
| `0x70` DSPFW0 | `0x0AB000` | `0x26008000` | `0x96000` | `0xBE000` | **DSP / HiFi5** (OTA img2) |
| `0x20` C0FW0 | `0x169000` | `0x34169020` | `0xAB690` | `0xC8000` | **app core** (OTA img3) |
| `0x90` | `0x231000` | 0 | 0 | `0x5A000` | spare / 2nd-slot region (empty) |
| `0x04` OTA | `0x28B000` | 0 | 0 | `0x15F000` | OTA staging area (1.4 MB, empty) |
| `0xC4` | `0x3EA000` | 0 | 0 | `0x2000` | data (empty) |
| `0xC3` | `0x3EC000` | 0 | 0 | `0x2000` | data (empty) |
| `0xC2` | `0x3EE000` | 0 | `0x1BEC` (7148) | `0x2000` | **config** (OTA img4, has model/BT-name) |
| `0xC1` | `0x3F0000` | 0 | `0x0E98` (3736) | `0x2000` | **"tone" partition** (OTA img5) |
| `0xC0` | `0x3F2000` | 0 | 0 | `0x2000` | data (empty) |
| `0x07` | `0x3F4000` | 0 | 0 | `0x8000` | data (empty, 32 KB) |
| `0x08` | `0x3FC000` | 0 | 0 | `0x2000` | data (empty) |
| `0x02` OEM | `0x3FE000` | 0 | 0 | `0x1000` | OEM / KV |
| `0x09` | `0x3FF000` | 0 | 0 | `0x1000` | KV / NV |

Flash ends at `0x400000` (~4 MB). **Key consequence:** the only non-empty data
partition that can hold prompt audio is the 8 KB `0x3F0000` "tone" region with 3736
bytes used. Every other data partition is empty or holds config/KV. There is **no
megabyte-scale voice-prompt partition** — not in this OTA, and not anywhere on the chip.
(The large empty `0x28B000` region is the OTA *download staging* area, not prompts.)

Note the boot-map image *type* for the tone region is the vendor-custom `0xC1`, **not**
the SDK's `IMAGE_TYPE_TONE = 5`. So the "tone" name is positional/by-convention (it is
OTA pack slot #5, mapped by `tools/ota_unpack.py`'s `NAMES` dict), **not** confirmed by a
type tag. Treat "tone" as a label, not proof of contents.

## 2. What is actually in the tone partition (`tone_0x003f0000.bin`, 3768 B)

Layout as parsed (offsets are within the extracted file; the first 32 B are the standard
`iot_flash_image_header_t`):

- `0x00–0x1F` — `iot_flash_image_header_t` ✅: guard `0xA4E49A17`, `length = 0xE98`
  (3736 = the bytes after this header), `version=0`, `start=0`, `crc=0xB3EE0DCA`,
  `tlv_count=0` (⇒ unsigned, consistent with [custom_firmware.md](custom_firmware.md)).
- `0x20–…` — the tone payload. It does **not** match the SDK's documented
  `tone_header_t` (`.../tone_storage/tone_storage.h`), whose first bytes would be
  `tone_num, language_num, version, codec_type`. Here those bytes are `00 00 00 01`
  (⇒ tone_num = 0, impossible) and the `sample_freq` field would read `0x57714F4D`
  (nonsense as a frequency). So **the N70 blob uses a different, undocumented tone
  container** than the old-arch `tone_storage` format in the SDK snapshot. (The ADK marks
  this area `#ifdef NEW_ARCH` → `nplayer_tone_*`; the snapshot ships only the headers, not
  the NEW_ARCH on-flash format, so we have no reference struct for it.)
- `0x24` carries a 4-byte tag `0x57714F4D` = ASCII **"MOqW"** — same `…qW` ("WuQi")
  family as the boot-map magic `0x5771424D` "WqBM", but a distinct value. Unidentified;
  best read as the tone-resource magic. Followed by what looks like a CRC
  (`0x23F7E472`) and a size `0x0E88` (3720 = file minus a 48-byte prefix).
- Two record tables follow (both made of **12-byte records** — note the SDK's old-arch
  on-flash `tone_table_t` is also "M × 12 bytes", but the fields do not validate as
  `(addr,len,sample_num)` here):
  - `~0x0A8–~0x0A40`: 12-byte records whose first word repeats (e.g. `0xE008044B`,
    `0xE1058ABB` recur every 12 bytes). As int16 pairs these resemble signed samples /
    filter coefficients. Moderate entropy (~6.0), not the ~8.0 of compressed/encrypted
    audio, and **not** further LZMA/zlib-compressed (tested).
  - `~0x0C00–0x0EB8`: 12-byte records dominated by **round decimal constants** —
    `0x000186A0` = 100 000, `0x00030D40` = 200 000, `0x000F4240` = 1 000 000, `0x00640000`.
    These look like **timing / duration / gain parameters** (µs or sample counts), i.e. a
    tone/beep *definition* table, not PCM.

Codec/signature evidence:
- The SDK's only tone codec enum value is `CODEC_MSBC_TYPE` (mSBC) — *source only*, and it
  belongs to the old-arch header the N70 does **not** use, so it is weak evidence here.
- **No standard audio-container signature** anywhere in any image: grep for `RIFF`,
  `WAVE`, `OggS`, `fLaC`, `OpusHead` → 0 hits. No LC3 either (confirmed earlier,
  [firmware_internals.md](firmware_internals.md)).
- The blob is **not** mSBC-framed in the obvious way (no 57-byte / `0xAD`-sync frame
  grid); its structure is 12-byte records, not codec frames.

**Best-supported inference (not confirmed):** the N70 prompts are **short synthesized
tones / beep melodies defined by small parameter records** (frequency / duration / gain),
not recorded speech. This fits every observation: the tiny 3736-byte size, the round-number
timing table, the 12-byte record structure, the absence of any audio container, and the
fact that there is no room (and no partition) for multilingual voice. The alternative —
a handful of very short mSBC clips — is not ruled out, but nothing positively supports it.
Either way, **"the sounds" are contained in this one partition.**

## 3. How a prompt is selected (language / index)

- The firmware plays a prompt by **event → tone_id**: `app_tone_indicate_event(event_id)`
  → `app_tone_send_play_msg(tone_id, …)` → `audio_player_tone_start()` /
  `player_tone_stop(tone_id)` which "find[s] tone data in flash" by id
  (`work/zt210-sdk/.../tone_play/play_tone.h`, `.../user_app/app_tone.c`). *Source only.*
- **Language** is set via `player_set_language()` / `tone_storage_language_set()` and, at
  the app layer, `qcy_to_wuqi_language_set(language_id, name)`. The app core
  (`app_core_riscv_0x00169000.bin` @ file offset `0xA0120`) holds four 8-byte **name
  tags** `WQ00 WQ01 WQ02 WQ03` — these are just *labels* reported up to the QCY app, with
  **no per-language audio** behind them on this product (there is no space and no second
  tone partition). So on the N70 the "language" control is effectively vestigial. ✅ that
  the tags exist and are tied to the language handler; inferred that they map to no real
  audio. A001 opcode for this is in [protocol.md](protocol.md).

## 4. Can we replace a sound by editing our OTA image? — verdict

**Partition-level: YES, mechanically feasible.** ✅
- The tone data is OTA pack image #5, so `tools/ota_unpack.py` already extracts it and
  `tools/ota_repack.py` will rebuild a flashable `.bin`, recomputing every CRC (including
  this image's `iot_flash_image_header_t.crc`, since it carries the `0xA4E49A17` guard).
- No secure boot, no signature, `tlv_count=0` ([custom_firmware.md](custom_firmware.md)).
  A modified tone partition with correct CRCs would be accepted and written to `0x3F0000`.
- Risk is comparatively low *as a brick risk*: this is a data partition, not boot/loader
  code (the SBL/boot ROM and the core images are untouched). A malformed tone blob would at
  worst make the tone player reject/garble prompts or fault at play time, recoverable by
  re-flashing a good image — it is not the boot path. (Still gated by the project's
  write-to-7033 rule; this doc is static only.)

**Content-level: NOT turnkey.** ⚠️ We cannot currently *author* a valid replacement sound:
- The tone container ("MOqW" magic, two 12-byte-record tables, likely NEW_ARCH
  `nplayer` format) is **not decoded** well enough to know how to encode a new clip, what
  the records mean, or which codec/format the player expects. We deliberately do **not**
  guess it (project rule: no fabricated formats, no unknown data to the device).
- The documented SDK `tone_storage` layout does **not** apply to this blob, so it is not a
  usable template.

**The real path to a working swap would be one of:**
1. **Decode the NEW_ARCH `nplayer` tone container** (the "MOqW" format): obtain the
   matching ADK NEW_ARCH tone sources / the WuQi UI "tone pack" tool (`.wpk`), which builds
   `tone.bin` from WAV + `tone.json`. That tooling is NDA/Windows and we do not have it
   ([sources.md](sources.md)). With it, rebuild the partition and repack via `ota_repack`.
2. **Read the live flash over UART** (`Wuqi.Beetle.Burn` single-wire) to dump/compare the
   partition and iterate on the format empirically — out of scope here (no device/UART).
3. If the tones are **synthesized from the parameter table** (the inference in §2), then a
   swap means *editing the beep parameters* (pitch/length), not dropping in an audio file —
   still blocked on decoding what the 12-byte records mean.

So: a drop-in "replace the power-on sound with my own clip" is **not possible today** from
statics alone; the OTA/repack plumbing is ready, but the tone-container format is the
missing piece.

## 5. Why there is no `tools/tone_unpack.py` (format is opaque)

Per the project rule against fabricating formats, no extractor is shipped: the tone blob
has **no clean, validating index** (no magic+count that yields `(offset,len)` clip entries
— the 12-byte records do not decode as addresses/lengths), and no known audio-container
framing. Writing a splitter would mean guessing. The structural findings above (header,
"MOqW" magic at `0x24`, the two 12-byte-record tables, offsets) are recorded so a future
worker with the NEW_ARCH tone sources or a UART flash dump can finish the decode and then
add a real extractor.

## 6. Status summary

| Claim | Status |
|---|---|
| Full flash partition map (15 partitions, ends `0x400000`) | ✅ parsed from img0 boot map |
| Only tone/prompt storage = `0x3F0000`, 3736 B, in OTA img5 | ✅ |
| No separate multilingual voice-prompt partition exists | ✅ (whole 4 MB map accounted for) |
| Tone partition is in-OTA and reachable via unpack/repack, no signing | ✅ |
| Prompt select = event→tone_id; language = WQ00–WQ03 name tags, no per-lang audio | ✅ tags / ⟶ inferred no audio |
| Tone blob codec/container | ⚠️ undocumented "MOqW" format; mSBC is SDK *source-only*, not confirmed; likely synthesized-tone params — **not decoded** |
| Swap a sound by editing our OTA image | partition-level ✅ feasible; content-level ⚠️ blocked on decoding the tone container |
