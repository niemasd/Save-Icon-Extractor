#! /usr/bin/env python3
'''
Extract the save game icon from a PSX disc image
'''

# imports
from niemafs import IsoFS
from pathlib import Path
from struct import unpack_from
from sys import stderr
from tqdm import tqdm
from warnings import filterwarnings
import argparse
import re

# hide warnings (e.g. NiemaFS)
filterwarnings('ignore')

# constants
DEFAULT_BUFSIZE = 1048576 # 1 MB
REGEX_TIM_4BIT = re.compile(rb'(?=\x10\x00\x00\x00[\x00-\x05\x08-\x0d]\x00\x00\x00)')

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
        raise ValueError(f"Output exists: {args.output}")
    return args

# attempt to read a TIM section starting at `pos`
def read_tim_section(data, pos, require_pixels):
    if pos + 12 > len(data):
        return None
    section_size, dest_x, dest_y, width_words, height = unpack_from('<IHHHH', data, pos)
    if section_size < 12:
        return None
    end = pos + section_size
    if end > len(data):
        return None
    if require_pixels and (width_words == 0 or height == 0):
        return None
    expected_size = 12 + (width_words * height * 2)
    padding = section_size - expected_size
    if padding not in (0, 2):
        return None
    return end

# attempt to parse the TIM starting at `start` in `data`, and return the end offset (or `None` if invalid)
def parse_tim_at(data, start):
    if start + 8 > len(data):
        return None
    flags = unpack_from('<I', data, start + 4)[0]
    if flags & ~0x0F:
        return None
    tim_type = flags & 0x07
    if tim_type > 5:
        return None
    has_clut = bool(flags & 0x08)
    pos = start + 8
    if has_clut:
        pos = read_tim_section(data, pos, require_pixels=False)
        if pos is None:
            return None
    pos = read_tim_section(data, pos, require_pixels=True)
    if pos is None:
        return None
    return pos

# extract all TIMs from the bytes of a file
def tims_from_data(data):
    found_ranges = list()
    for match in REGEX_TIM_4BIT.finditer(data):
        start = match.start()
        end = parse_tim_at(data, start)
        if (end is None) or (found_ranges and start < found_ranges[-1][1]):
            continue
        found_ranges.append((start, end))
    return [data[start:end] for start, end in found_ranges]

# main program logic
def main(bufsize=DEFAULT_BUFSIZE):
    # load files from input disc image
    args = parse_args()
    if not args.quiet:
        print(f"Input PSX Disc Image: {args.input}", file=stderr)
    with open(args.input, 'rb', buffering=bufsize) as iso_f:
        it = IsoFS(iso_f)
        if not args.quiet:
            it = tqdm(it, desc="Loading disc contents")
        files = {curr_path:curr_data for curr_path, curr_timestamp, curr_data in it if curr_data}

    # scan files for TIM icon data
    icons = dict()
    it = files.items()
    if not args.quiet:
        it = tqdm(it, desc="Scanning loaded files", total=len(files))
    for curr_path, curr_data in it:
        icons[curr_path] = tims_from_data(curr_data)
    num_icons = sum(len(v) for v in icons.values())
    if num_icons == 0:
        if not args.quiet:
            print(f"No icons found", file=stderr)
        return

    # write found icons to output folder
    if not args.quiet:
        print(f"Writing {num_icons} icon(s) to output: {args.output}", file=stderr)
    args.output.mkdir()
    it = sorted(icons.items())
    if not args.quiet:
        it = tqdm(it, desc="Writing TIM(s) from disc file", total=len(icons))
    for p, tims in it:
        if len(tims) == 0:
            continue
        curr_out = args.output / str(p).split(';')[0].strip()

        # entire file was a single TIM
        if len(tims) == 1 and len(tims[0]) == len(files[p]):
            curr_out.parent.mkdir(exist_ok=True, parents=True)
            with open(curr_out, mode='wb', buffering=bufsize) as tim_f:
                tim_f.write(tims[0])

        # file contained multiple TIMs
        else:
            curr_out.mkdir(parents=True)
            int_len = len(str(len(tims)-1))
            for i, tim_data in enumerate(tims):
                with open(curr_out / f'{str(i).zfill(int_len)}.tim', mode='wb', buffering=bufsize) as tim_f:
                    tim_f.write(tim_data)

# run tool
if __name__ == "__main__":
    main()
