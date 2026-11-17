#!/usr/bin/env python3
# Repack a QCY/WuQi WQ703X OTA firmware image: the inverse of tools/ota_unpack.py.
#
# Takes a directory of decompressed images (as ota_unpack.py writes them, plus
# its manifest.json) and produces a valid, flashable OTA .bin. The device accepts
# images on guard-magic + CRC-32 only -- no signature, no secure boot, no
# encryption (see docs/custom_firmware.md) -- so a repack with correct CRCs is
# flashable in principle. This tool writes a file; it does NOT touch any device.
#
# What it rebuilds (mirrors ota_unpack.py / the SDK ota.c + iot_loader.c):
#
#   * Per code image: if the image carries the iot_flash_image_header_t guard
#     0xA4E49A17, its header.crc is recomputed as CRC-32 over the code bytes that
#     follow the 32-byte header, byte count = header.length. (Discovered by
#     recomputing against the stock extracted images; all five guarded images
#     match byte-for-byte. See docs/firmware.md.) This makes an in-place code
#     patch self-consistent without any manual CRC edit.
#   * Each image is LZMA-compressed with lzma.FORMAT_ALONE -- the exact inverse
#     of ota_unpack.py's lzma.decompress(..., format=lzma.FORMAT_ALONE).
#   * pack_desc_t (magic, fw_version, image_pack_types, time_stamp) + image_desc[]
#     (image_size, image_compress_size, image_start_addr, image_end_addr), from
#     the manifest with image_compress_size recomputed.
#   * header_crc = CRC-32 over image_desc[]; data_crc = CRC-32 over the
#     concatenated compressed blocks (both standard zlib crc32).
#   * The 18-byte big-endian ota_file_header_t wrapper: VID/PID/version/reserved
#     copied from the manifest, len = (total file size - 18), crc = CRC-32 over
#     every byte after the 18-byte wrapper.
#
# Note on byte-identity: WuQi's LZMA encoder is not Python's, so the compressed
# blocks (and therefore the whole file) will usually NOT be byte-identical to the
# stock .bin. That is expected and fine. The contract is the SEMANTIC round-trip:
# the rebuilt file has valid CRCs and every image decompresses back to the exact
# input bytes. --selftest proves exactly that against the stock .bin.
#
# Usage:
#   python3 -I tools/ota_repack.py <extracted_dir> <out.bin> [--ref <stock.bin>]
#   python3 -I tools/ota_repack.py --selftest <stock.bin> [work_dir]
#
# <extracted_dir> must contain the image files; metadata comes from
# <extracted_dir>/manifest.json, or from --ref <stock.bin> if no manifest exists.

import sys, os, struct, zlib, lzma, json, tempfile, shutil

MAGIC = 0xABCD6543
GUARD = 0xA4E49A17
IMG_HDR_LEN = 0x20  # sizeof(iot_flash_image_header_t)
NAMES = {0: "img0_bootmap", 1: "bt_core_riscv", 2: "dsp_hifi5_xtensa",
         3: "app_core_riscv", 4: "img4_cfg", 5: "tone"}


def crc32(buf):
    return zlib.crc32(buf) & 0xFFFFFFFF


def fix_image_header_crc(raw):
    """If raw is a guarded code image, return it with header.crc recomputed.

    header.crc = CRC-32 over raw[0x20 : 0x20 + header.length]. For an in-place
    code patch that keeps the size, header.length is unchanged and this is the
    only field that needs fixing. Returns raw untouched if there is no guard.
    """
    if len(raw) < IMG_HDR_LEN:
        return raw
    guard, length, _ver, _start, old_crc = struct.unpack_from("<IIIII", raw, 0)
    if guard != GUARD:
        return raw  # e.g. img0_bootmap has no guard; pass through verbatim.
    body = raw[IMG_HDR_LEN:]
    if length != len(body):
        print(f"  warning: header.length={length} != body bytes={len(body)}; "
              f"image was resized. CRC is computed over header.length bytes; "
              f"update header.length yourself if that is wrong.")
    new_crc = crc32(body[:length])
    if new_crc != old_crc:
        print(f"  image header crc updated 0x{old_crc:08x} -> 0x{new_crc:08x}")
    out = bytearray(raw)
    struct.pack_into("<I", out, 16, new_crc)  # crc is the 5th u32 (offset 16)
    return bytes(out)


def load_metadata(extracted_dir, ref_bin):
    """Return (wrapper, pack, images) from manifest.json or by parsing ref_bin."""
    mpath = os.path.join(extracted_dir, "manifest.json")
    if os.path.exists(mpath):
        with open(mpath) as fh:
            m = json.load(fh)
        return m["wrapper"], m["pack_desc"], m["images"]
    if not ref_bin:
        raise SystemExit(f"error: no {mpath} and no --ref <stock.bin> given; "
                         "cannot recover addresses / pack types / VID/PID")
    return parse_ref(ref_bin)


def parse_ref(ref_bin):
    """Parse a stock .bin for its metadata (fallback when no manifest exists)."""
    data = open(ref_bin, "rb").read()
    off = data.find(struct.pack("<I", MAGIC))
    if off < 0:
        raise SystemExit("error: pack_desc magic not found in --ref file")
    w_vid, w_pid, w_ver = struct.unpack_from(">HHH", data, off - 18)
    _w_len, w_res, _w_crc = struct.unpack_from(">III", data, off - 18 + 6)
    wrapper = {"vid": w_vid, "pid": w_pid, "version": w_ver, "reserved": w_res}
    magic, fw_version, pack_types, ts = struct.unpack_from("<IIII", data, off)
    n = bin(pack_types).count("1")
    pack = {"fw_version": fw_version, "image_pack_types": pack_types,
            "time_stamp": ts}
    images = []
    base = off + 16
    for i in range(n):
        isz, _csz, sa, ea = struct.unpack_from("<IIII", data, base + i * 16)
        name = NAMES.get(i, f"img{i}")
        images.append({"index": i, "file": f"{name}_0x{sa:08x}.bin",
                       "image_size": isz, "image_start_addr": sa,
                       "image_end_addr": ea})
    return wrapper, pack, images


def repack(extracted_dir, out_bin, ref_bin=None):
    wrapper, pack, images = load_metadata(extracted_dir, ref_bin)
    images = sorted(images, key=lambda d: d["index"])

    descs = []
    blocks = []
    for img in images:
        path = os.path.join(extracted_dir, img["file"])
        if not os.path.exists(path):
            raise SystemExit(f"error: missing image {path}")
        raw = open(path, "rb").read()
        raw = fix_image_header_crc(raw)
        comp = lzma.compress(raw, format=lzma.FORMAT_ALONE)
        # Safety: the inverse must hold before we ship the block.
        if lzma.decompress(comp, format=lzma.FORMAT_ALONE) != raw:
            raise SystemExit(f"error: LZMA round-trip failed for {img['file']}")
        descs.append((len(raw), len(comp), img["image_start_addr"],
                      img["image_end_addr"]))
        blocks.append(comp)
        print(f"img[{img['index']}] {img['file']:34s} raw={len(raw)} "
              f"comp={len(comp)} start=0x{img['image_start_addr']:08x}")

    desc_bytes = b"".join(struct.pack("<IIII", *d) for d in descs)
    header_crc = crc32(desc_bytes)
    comp_blob = b"".join(blocks)
    data_crc = crc32(comp_blob)

    pack_desc = struct.pack("<IIII", MAGIC, pack["fw_version"],
                            pack["image_pack_types"], pack["time_stamp"])
    payload = (pack_desc + desc_bytes + struct.pack("<I", header_crc)
               + comp_blob + struct.pack("<I", data_crc))

    w_crc = crc32(payload)
    w_len = len(payload)
    wrapper_hdr = struct.pack(">HHH", wrapper["vid"], wrapper["pid"],
                              wrapper["version"])
    wrapper_hdr += struct.pack(">III", w_len, wrapper["reserved"], w_crc)

    out = wrapper_hdr + payload
    with open(out_bin, "wb") as fh:
        fh.write(out)
    print(f"header_crc=0x{header_crc:08x}  data_crc=0x{data_crc:08x}  "
          f"wrapper_crc=0x{w_crc:08x}")
    print(f"wrote {len(out)} bytes -> {out_bin}")
    return out_bin


def selftest(stock_bin, work_dir=None):
    """unpack(stock) -> repack -> unpack(repack); assert CRCs + payload identity."""
    here = os.path.dirname(os.path.abspath(__file__))
    unpack = os.path.join(here, "ota_unpack.py")
    tmp = work_dir or tempfile.mkdtemp(prefix="ota_selftest_")
    os.makedirs(tmp, exist_ok=True)
    ext0 = os.path.join(tmp, "stock_extracted")
    ext1 = os.path.join(tmp, "repack_extracted")
    repacked = os.path.join(tmp, "repack.bin")

    import runpy
    def run_unpack(src, dst):
        saved = sys.argv
        sys.argv = [unpack, src, dst]
        try:
            runpy.run_path(unpack, run_name="__main__")
        except SystemExit:
            pass
        finally:
            sys.argv = saved

    print("== unpack stock ==")
    run_unpack(stock_bin, ext0)
    print("\n== repack ==")
    repack(ext0, repacked)  # uses ext0/manifest.json
    print("\n== unpack repack ==")
    run_unpack(repacked, ext1)

    print("\n== verify ==")
    ok = True
    # (a) CRCs verify: re-run the exact checks ota_unpack does, silently here.
    rp = open(repacked, "rb").read()
    off = rp.find(struct.pack("<I", MAGIC))
    _m, _fw, pt, _ts = struct.unpack_from("<IIII", rp, off)
    n = bin(pt).count("1")
    db = off + 16
    descs = [struct.unpack_from("<IIII", rp, db + i * 16) for i in range(n)]
    hc_off = db + n * 16
    saved_h = struct.unpack_from("<I", rp, hc_off)[0]
    calc_h = crc32(rp[db:hc_off])
    comp_off = hc_off + 4
    total = sum(c for _, c, _, _ in descs)
    saved_d = struct.unpack_from("<I", rp, comp_off + total)[0]
    calc_d = crc32(rp[comp_off:comp_off + total])
    w_len, w_res, w_crc = struct.unpack_from(">III", rp, off - 18 + 6)
    calc_w = crc32(rp[off - 18 + 18:])
    print(f"header CRC: {'OK' if saved_h == calc_h else 'FAIL'}")
    print(f"data   CRC: {'OK' if saved_d == calc_d else 'FAIL'}")
    print(f"wrapper CRC:{'OK' if w_crc == calc_w else 'FAIL'} "
          f"(len {'OK' if w_len == len(rp) - 18 else 'FAIL'})")
    ok &= (saved_h == calc_h) and (saved_d == calc_d) and (w_crc == calc_w)
    ok &= (w_len == len(rp) - 18)

    # (b) every decompressed image is byte-identical to the stock extraction.
    for fn in sorted(os.listdir(ext0)):
        if not fn.endswith(".bin"):
            continue
        a = open(os.path.join(ext0, fn), "rb").read()
        b = open(os.path.join(ext1, fn), "rb").read()
        same = a == b
        ok &= same
        print(f"payload {fn:34s} {'identical' if same else 'DIFFERS'}")

    # (c) report (not required): whole-file byte identity with the stock .bin.
    stock = open(stock_bin, "rb").read()
    identical_file = stock == rp
    print(f"\nwhole-file byte-identical to stock: {identical_file} "
          f"(not required; WuQi's LZMA encoder differs from Python's)")
    print(f"\nSELFTEST {'PASS' if ok else 'FAIL'}")
    if work_dir is None:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1


def main(argv):
    if len(argv) >= 2 and argv[1] == "--selftest":
        if len(argv) < 3:
            print(__doc__)
            return 1
        return selftest(argv[2], argv[3] if len(argv) > 3 else None)
    if len(argv) < 3:
        print(__doc__)
        return 1
    extracted_dir, out_bin = argv[1], argv[2]
    ref = None
    if "--ref" in argv:
        ref = argv[argv.index("--ref") + 1]
    repack(extracted_dir, out_bin, ref)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
