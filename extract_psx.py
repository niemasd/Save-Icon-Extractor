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
REGEX_CNF_BOOT = r"BOOT\s*=\s*cdrom:\\?([^\s\n\r]+)"
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

# parse save icons from a PSX disc image file stream
def parse_icons(file_obj, quiet=False):
    # load files from PSX disc image
    it = IsoFS(file_obj)
    if not quiet:
        it = tqdm(it, desc="Loading files from disc image")
    files = {curr_path:curr_data for curr_path, curr_timestamp, curr_data in it}
    try:
        cnf_path, cnf_data = [(p, d) for p, d in files.items() if p.name.upper().startswith('SYSTEM.CNF')][0]
    except IndexError:
        raise ValueError("Invalid PSX disc image: file 'SYSTEM.CNF' not found")

    # determine main EXE from SYSTEM.CNF
    if not quiet:
        print("Finding executable path from 'SYSTEM.CNF'...", file=stderr)
    match = re.match(REGEX_CNF_BOOT, cnf_data.decode(), re.IGNORECASE)
    if not match:
        raise ValueError("Invalid PSX disc image: no 'BOOT' line in 'SYSTEM.CNF'")
    exe_path = Path(match.group(1).strip())
    if not quiet:
        print(f"Executable determined from 'SYSTEM.CNF': {exe_path}")

    # scan executable for save data
    try:
        exe_data = files[exe_path]
    except KeyError:
        raise ValueError(f"Invalid PSX disc image: executable '{exe_path}' not on disc")
    it = range(len(exe_data) - 352)
    if not quiet:
        it = tqdm(it, desc=f"Scanning '{exe_path}' for save data")
    icons = list()
    for offset in it:
        # skip if no save data header magic bytes
        if exe_data[offset : offset + 2] != b'SC':
            continue

        # parse icon type + block count (and skip if invalid)
        icon_type = exe_data[offset + 2]
        if icon_type not in ICON_TYPES:
            continue
        block_count = data[offset + 3]
        if block_count < 1 or block_count > 15:
            continue

        # parse icon block (352 bytes: 0-63 = header/title, 64-95 = reserved, 96-223 = 16-color CLUT, 224-351 = 4-bit bitmap)
        num_frames = icon_type & 0x0F
        total_icon_size = 224 + (num_frames * 128)
        icon_data = exe_data[offset : offset + total_icon_size]
        icons.append(icon_data)
    return icons

# main program logic
def main():
    args = parse_args()
    if not args.quiet:
        print(f"Input PSX Disc Image: {args.input}", file=stderr)
    with open(args.input, 'rb', buffering=DEFAULT_BUFSIZE) as f:
        icons = parse_icons(f, quiet=args.quiet)
    if len(icons) == 0:
        print(f"No icons found", file=stderr)
    else:
        print(f"Writing icons to output: {args.output}", file=stderr)

# run tool
if __name__ == "__main__":
    main()
