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
    if len(data) < 8:
        raise ValueError("Invalid TIM: File is too small.")
    magic, tim_type = unpack('<II', data[0:8])
    if magic != 0x10:
        raise ValueError(f"Invalid TIM signature: Expected 0x10, got {hex(magic)}")
    has_clut = (tim_type & 0x08) != 0
    bpp_mode = tim_type & 0x03  # 0=4bit, 1=8bit, 2=16bit, 3=24bit
    offset = 8
    clut_colors = list()
    if has_clut:
        if offset + 12 > len(data):
            raise ValueError("Malformed TIM: Truncated CLUT header.")
        clut_block_size, cx, cy, cw, ch = unpack('<IHHHH', data[offset:offset+12])
        total_colors = cw * ch
        clut_data_offset = offset + 12
        if offset + clut_block_size > len(data):
            raise ValueError("Malformed TIM: CLUT block out of bounds.")
        for i in range(total_colors):
            p_offset = clut_data_offset + (i * 2)
            if p_offset + 2 <= len(data):
                pixel = unpack_from('<H', data, p_offset)[0]
                r =  (pixel        & 0x1F) << 3
                g = ((pixel >>  5) & 0x1F) << 3
                b = ((pixel >> 10) & 0x1F) << 3
                a = 0xFF if (pixel & 0x8000) or (r or g or b) else 0x00
                clut_colors.append((r, g, b, a))
        offset += clut_block_size
    if offset + 12 > len(data):
        raise ValueError("Malformed TIM: Missing or truncated image data header.")
    img_block_size, dx, dy, w, h = unpack('<IHHHH', data[offset : offset + 12])
    pixel_data_size = img_block_size - 12
    if offset + img_block_size > len(data):
        raise ValueError(f"Malformed TIM: Extracted image data segment is truncated. "
                         f"Expected {img_block_size} bytes in block, but only {len(data) - offset} remain.")
    pixel_data = data[offset + 12 : offset + img_block_size]
    if w == 0 or h == 0:
        raise ValueError(f"Invalid structural layout: Zero image boundaries ({w}x{h}).")
    if bpp_mode == 0:    # 4-bit Indexed
        pixel_width = w * 4
    elif bpp_mode == 1:  # 8-bit Indexed
        pixel_width = w * 2
    elif bpp_mode == 2:  # 16-bit Direct Color
        pixel_width = w
    elif bpp_mode == 3:  # 24-bit Direct Color
        pixel_width = (w * 2) // 3
    else:
        raise ValueError(f"Unsupported TIM bit depth configuration: {bpp_mode}")
    rgba_output = bytearray()
    if bpp_mode == 0:  # 4-bit (Each byte holds two 4-bit indices)
        for byte in pixel_data:
            idx1 = byte & 0x0F
            idx2 = (byte >> 4) & 0x0F
            rgba_output.extend(clut_colors[idx1] if idx1 < len(clut_colors) else (0,0,0,0))
            rgba_output.extend(clut_colors[idx2] if idx2 < len(clut_colors) else (0,0,0,0))
    elif bpp_mode == 1:  # 8-bit (Each byte holds one 8-bit index)
        for byte in pixel_data:
            rgba_output.extend(clut_colors[byte] if byte < len(clut_colors) else (0,0,0,0))
    elif bpp_mode == 2:  # 16-bit Direct Color
        for i in range(0, len(pixel_data), 2):
            if i + 1 < len(pixel_data):
                pixel = unpack_from('<H', pixel_data, i)[0]
                r =  (pixel        & 0x1F) << 3
                g = ((pixel >>  5) & 0x1F) << 3
                b = ((pixel >> 10) & 0x1F) << 3
                a = 0xFF if (pixel & 0x8000) else 0x00
                rgba_output.extend([r, g, b, a])
    elif bpp_mode == 3:  # 24-bit Direct Color (Standard raw RGB bytes)
        for i in range(0, len(pixel_data), 3):
            if i + 2 < len(pixel_data):
                rgba_output.extend([pixel_data[i], pixel_data[i+1], pixel_data[i+2], 0xFF])
    expected_bytes = pixel_width * h * 4
    if len(rgba_output) < expected_bytes:
        rgba_output.extend([0] * (expected_bytes - len(rgba_output)))
    return Image.frombytes('RGBA', (pixel_width, h), bytes(rgba_output))

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
