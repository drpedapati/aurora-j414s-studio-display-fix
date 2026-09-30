#!/usr/bin/env python3
"""Decode diagnostic ADT copies; read files only, never MMIO or device nodes."""
import pathlib
import struct
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/proc/device-tree/chosen")
reference = [
    (0x20C, 0xFF0000B7, 0xE40000B7),
    (0x220, 0x000F0F0F, 0x000F0F0F),
    (0x224, 0x00FFFFFF, 0x00080808),
    (0x300, 0x00001F31, 0x00000001),
    (0x308, 0x3FFFFFFC, 0x10000000),
    (0x310, 0x3FFFFFFC, 0x3FFFFFFC),
]
for port in range(3):
    prefix = root / f"asahi,diagnostic-pciec-dart{port}"
    status = pathlib.Path(str(prefix) + "-status")
    raw = pathlib.Path(str(prefix) + "-raw")
    print(f"Port {port}: {status.read_bytes().rstrip(bytes([0])).decode() if status.exists() else 'not exported'}")
    if not raw.exists():
        continue
    data = raw.read_bytes()
    if not data or len(data) > 4096 or len(data) % 24:
        raise SystemExit("Invalid diagnostic length")
    records = []
    for offset, size, mask, value in struct.iter_unpack("<IIQQ", data):
        if size != 4 or offset % 4 or offset > 0x4000 - 4:
            raise SystemExit("Unsupported access size, alignment, or DART offset")
        if mask > 0xFFFFFFFF or value > 0xFFFFFFFF:
            raise SystemExit("Tunable exceeds 32 bits")
        records.append((offset, mask, value))
        print(f"  <0x{offset:03x} 0x{mask:08x} 0x{value:08x}>")
    print("  Matches PR50 J416c reference:", records == reference)
