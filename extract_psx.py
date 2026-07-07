#! /usr/bin/env python3
'''
Extract the save game icon from a PSX disc image
'''

# imports
from niemafs import IsoFS
from pathlib import Path
from sys import stderr
from tqdm import tqdm
from warnings import filterwarnings
import argparse
import re

# hide warnings (e.g. NiemaFS)
filterwarnings('ignore')

# constants
DEFAULT_BUFSIZE = 1048576 # 1 MB
REGEX_TIM_4BIT = re.compile(b'\x10\x00\x00\x00\x08\x00\x00\x00')
ICON_TYPES = {0x11, 0x12, 0x13}

# parse user args
def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--input', required=True, type=str, help="Input PSX Disc Image")
    parser.add_argument('-o', '--output', required=True, type=str, help="Output Folder")
    parser.add_argument('-q', '--quiet', action='store_true', help="Suppress Progress Messages")
    args = parser.parse_args()
    args.input = Path(args.input)
    if not args.input.is_file():
        raise ValueError(f"File not found: {args.input}")
    args.output = Path(args.output)
    if args.output.exists():
        raise ValueError(f"Output folder exists: {args.output}")
    return args

# parse icons from a PSX disc image file stream
def parse_icons(file_obj, quiet=False):
    it = IsoFS(file_obj)
    if not quiet:
        it = tqdm(it, desc="Scanning disc files")
    icons = list()
    for curr_path, curr_timestamp, curr_data in it:
        if curr_data is None:
            continue # skip folders
        for match in REGEX_TIM_4BIT.finditer(curr_data):
            offset = match.start()
            if len(curr_data) < offset + 16:
                continue
            clut_size = int.from_bytes(curr_data[offset+8 : offset+12], byteorder='little')
            img_size_offset = offset + 12 + clut_size
            if len(curr_data) < img_size_offset + 4:
                continue
            img_size = int.from_bytes(curr_data[img_size_offset : img_size_offset+4], byteorder='little')
            total_tim_size = 12 + clut_size + img_size
            if len(curr_data) < (offset + total_tim_size):
                continue
            icons.append(curr_data[offset : offset + total_tim_size])
    return icons

# main program logic
def main(bufsize=DEFAULT_BUFSIZE):
    args = parse_args()
    if not args.quiet:
        print(f"Input PSX Disc Image: {args.input}", file=stderr)
    with open(args.input, 'rb', buffering=bufsize) as iso_f:
        icons = parse_icons(iso_f, quiet=args.quiet)
    if len(icons) == 0:
        if not args.quiet:
            print(f"No icons found", file=stderr)
        return
    if not args.quiet:
        print(f"Writing {len(icons)} icon(s) to output: {args.output}", file=stderr)
    args.output.mkdir()
    int_len = len(str(len(icons)-1))
    it = enumerate(icons)
    if not args.quiet:
        it = tqdm(it, desc='Writing TIM file', total=len(icons))
    for i, tim_data in it:
        with open(args.output / f'{str(i).zfill(int_len)}.tim', mode='wb', buffering=bufsize) as tim_f:
            tim_f.write(tim_data)

# run tool
if __name__ == "__main__":
    main()
