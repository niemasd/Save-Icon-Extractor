#! /usr/bin/env python3
'''
Convert a PSX TIM icon to standard image format (e.g. PNG)
'''

# imports
from pathlib import Path
from PIL import Image
from struct import unpack, unpack_from
from sys import stderr
import argparse

# constants
DEFAULT_BUFSIZE = 1048576 # 1 MB

# parse user args
def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str, help="Input TIM File")
    parser.add_argument('-o', '--output', required=True, type=str, help="Output Image File")
    parser.add_argument('-q', '--quiet', action='store_true', help="Suppress Progress Messages")
    args = parser.parse_args()
    args.input = Path(args.input)
    if not args.input.is_file():
        raise ValueError(f"File not found: {args.input}")
    args.output = Path(args.output)
    if args.output.exists():
        raise ValueError(f"Output exists: {args.output}")
    return args

# load TIM as PIL image
def load_tim(data):
    magic, tim_type = unpack('<II', data[0 : 8])
    if magic != 0x10:
        raise ValueError("Invalid TIM: missing magic 0x10")
    has_clut = (tim_type & 0x08) != 0
    offset = 8
    if has_clut:
        clut_block_size = unpack('<I', data[offset : offset + 4])[0]
        offset += clut_block_size
    if offset + 12 > len(data):
        raise ValueError("Invalid TIM: missing image header block")
    img_block_size, dx, dy, w, h = unpack('<IHHHH', data[offset : offset+12])
    offset += 12
    if (w == 0) or (h == 0):
        raise ValueError(f"Invalid image dimensions extracted: {w}x{h}")
    pixel_data_size = w * h * 2
    pixel_data = data[offset : offset + pixel_data_size]
    rbga_data = bytearray()
    for i in range(0, len(pixel_data), 2):
        pixel = unpack_from('<H', pixel_data, i)[0]
        r =  (pixel        & 0x1F) << 3
        g = ((pixel >>  5) & 0x1F) << 3
        b = ((pixel >> 10) & 0x1F) << 3
        a = 0xFF if (pixel & 0x8000) else 0x00
        rbga_data.extend([r, g, b, a])
    return Image.frombytes('RGBA', (w,h), bytes(rbga_data))

# main program logic
def main(bufsize=DEFAULT_BUFSIZE):
    args = parse_args()
    if not args.quiet:
        print(f"Loading input TIM File: {args.input}", file=stderr)
    with open(args.input, mode='rb', buffering=bufsize) as tim_f:
        img = load_tim(tim_f.read())
    if not args.quiet:
        print(f"Writing to output file: {args.output}", file=stderr)
    img.save(args.output)

# run tool
if __name__ == "__main__":
    main()
