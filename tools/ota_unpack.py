#!/usr/bin/env python3
# Unpack a QCY/WuQi WQ703X OTA firmware image (e.g. HT18 = QCY MeloBuds N70).
#
# The OTA .bin is NOT encrypted. Layout (little-endian unless noted):
#
#   ota_file_header_t   18 bytes, big-endian fields (prepended for transfer):
#       vid(2) pid(2) version(2) len(4) reserved(4) crc(4)
#   pack_desc_t         16 bytes:
#       magic(4)=0xABCD6543  fw_version(4)  image_pack_types(4)  time_stamp(4)
#   image_desc[N]       16 bytes each, N = popcount(image_pack_types):
#       image_size(4)  image_compress_size(4)  image_start_addr(4)  image_end_addr(4)
#   header_crc(4)       CRC-32 over the image_desc[] array
#   <compressed blocks> each image, concatenated; every block is a standard
#                       .lzma (LZMA_ALONE) stream, so its own 13-byte header
#                       carries props + dict size + uncompressed size
#   data_crc(4)         CRC-32 over all the compressed blocks
#
# CRC-32 is standard zlib crc32. Struct and magic come from the public WuQi
# SDK source (ota.h / ota.c). See docs/firmware.md.
#
# Usage:  python3 -I tools/ota_unpack.py <firmware.bin> [out_dir]
# Writes one decompressed image per block and verifies both CRCs.

import sys, os, struct, zlib, lzma

MAGIC = 0xABCD6543
NAMES = {  # roles confirmed from headers + strings (see docs/firmware_internals.md)
    0: "img0_bootmap", 1: "bt_core_riscv", 2: "dsp_hifi5_xtensa",
    3: "app_core_riscv", 4: "img4_cfg", 5: "tone",
}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    data = open(argv[1], "rb").read()
    out_dir = argv[2] if len(argv) > 2 else argv[1] + ".extracted"

    off = data.find(struct.pack("<I", MAGIC))
    if off < 0:
        print("error: pack_desc magic 0xABCD6543 not found")
        return 2
    print(f"file {len(argv[1])} bytes={len(data)}  pack_desc at 0x{off:x}"
          f"  (prefix {off} bytes = ota_file_header_t)")

    magic, fw_version, pack_types, ts = struct.unpack_from("<IIII", data, off)
    n = bin(pack_types).count("1")
    print(f"fw_version={fw_version} pack_types=0x{pack_types:x} ({n} images) "
          f"time_stamp=0x{ts:08x}")

    desc_base = off + 16
    descs = [struct.unpack_from("<IIII", data, desc_base + i * 16) for i in range(n)]

    hdr_crc_off = desc_base + n * 16
    saved = struct.unpack_from("<I", data, hdr_crc_off)[0]
    calc = zlib.crc32(data[desc_base:hdr_crc_off]) & 0xFFFFFFFF
    print(f"header CRC: {'OK' if saved == calc else 'MISMATCH'} "
          f"(0x{saved:08x} vs 0x{calc:08x})")

    comp_off = hdr_crc_off + 4
    total = sum(c for _, c, _, _ in descs)
    saved_d = struct.unpack_from("<I", data, comp_off + total)[0]
    calc_d = zlib.crc32(data[comp_off:comp_off + total]) & 0xFFFFFFFF
    print(f"data   CRC: {'OK' if saved_d == calc_d else 'MISMATCH'} "
          f"(0x{saved_d:08x} vs 0x{calc_d:08x})")

    os.makedirs(out_dir, exist_ok=True)
    o = comp_off
    for i, (isz, csz, sa, ea) in enumerate(descs):
        block = data[o:o + csz]
        o += csz
        try:
            raw = lzma.decompress(block, format=lzma.FORMAT_ALONE)
        except Exception as e:  # noqa: BLE001
            print(f"img[{i}] start=0x{sa:08x} comp={csz}: decompress failed: {e}")
            continue
        ok = "OK" if len(raw) == isz else f"size {len(raw)}!={isz}"
        name = NAMES.get(i, f"img{i}")
        path = os.path.join(out_dir, f"{name}_0x{sa:08x}.bin")
        open(path, "wb").write(raw)
        print(f"img[{i}] start=0x{sa:08x} comp={csz} -> raw={len(raw)} {ok}  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
