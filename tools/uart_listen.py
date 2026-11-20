#!/usr/bin/env python3
"""Read-only UART listener for the QCY MeloBuds Pro boot log.

Opens the serial port at a given baud, reads for `duration` seconds, and dumps
whatever arrives as ASCII (printable) plus a hex preview. Trigger a device
reboot (take the bud out of the case) while this runs to catch the boot log.

Usage:
  python3 -I uart_listen.py /dev/cu.usbserial-XXXX 1500000 [duration_s]

Nothing is ever transmitted (RX-only). Safe to run repeatedly at different bauds.
Common WuQi/TWS bauds to try: 115200 921600 1500000 2000000 3000000.
"""
import sys, time

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    port = sys.argv[1]
    baud = int(sys.argv[2])
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
    try:
        import serial  # pyserial
    except ImportError:
        print("pyserial missing: pip3 install --user pyserial"); sys.exit(2)

    ser = serial.Serial(port, baud, timeout=0.2)
    # Do NOT drive the line: keep RTS/DTR deasserted, never write.
    try:
        ser.rts = False; ser.dtr = False
    except Exception:
        pass
    print(f"[listening] {port} @ {baud} baud for {dur:.0f}s — reboot the bud now (take it out of the case)")
    buf = bytearray()
    t0 = time.time()
    try:
        while time.time() - t0 < dur:
            chunk = ser.read(4096)
            if chunk:
                buf += chunk
                sys.stdout.write(chunk.decode("ascii", "replace"))
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
    printable = sum(1 for b in buf if 9 <= b <= 13 or 32 <= b <= 126)
    total = len(buf)
    print(f"\n\n[summary] {total} bytes, {printable} printable "
          f"({100*printable/total:.0f}% )" if total else "\n[summary] 0 bytes — wrong pad/baud/level, or no TX here")
    if total:
        print("[hex head]", buf[:64].hex())

if __name__ == "__main__":
    main()
