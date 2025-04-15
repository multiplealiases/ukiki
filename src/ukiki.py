#!/usr/bin/env python3
"""
Make UKIs using objcopy.
"""

from pathlib import Path
import sys
import argparse
import platform
import re
import tempfile
import subprocess

# This script requires Python 3.9.

# ukiki: make UKIs using objcopy

# SPDX-License-Identifier: MIT

# Copyright (c) 2025 multiplealiases
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# “Software”), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
# THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# one-number pride versioning:
# increment every time the author is proud of the release
__version__ = "0"


def guess_efistub(arch):
    arch = translate_machine(arch)

    guesslist = [
        Path(f"./linux{arch}.efi.stub"),
        Path(f"/usr/lib/systemd/boot/efi/linux{arch}.efi.stub"),
        Path(f"/usr/lib/gummiboot/linux{arch}.efi.stub"),
    ]

    for p in guesslist:
        if p.exists():
            return p

    sys.exit(f"""The EFI stub linux{arch}.efi.stub (required to produce a UKI)
is absent, and no candidate exists in the filesystem.

The following distributions are known to package
a suitable stub under the following package names.

Alpine: gummiboot-efistub
Arch: systemd
Chimera: systemd-boot-efi
Debian Bookworm, Ubuntu 24.04+: systemd-boot-efi
Fedora: systemd-boot-unsigned
Gentoo: sys-apps/systemd[boot] or sys-apps/systemd-utils[boot]
Void: systemd-boot-efistub

You may also specify -e/--efistub to skip autodetection.""")


def translate_machine(arch):
    # architecture mapping taken from efi-mkuki.
    if arch in ("x86_64", "x64", "amd64"):
        return "x64"
    if re.search(R"i[34567]86", arch) or arch == "ia32":
        return "ia32"
    if arch in ("arm64", "aarch64", "aa64"):
        return "aa64"
    if re.search(R"arm.*", arch):
        return "arm"
    sys.exit(f"Unknown architecture {arch}. Specify -e/--efistub.")


def parse_last_section(efistub) -> int:
    output = subprocess.check_output(["objdump", "--section-headers", efistub])
    line = re.search(
        r".reloc\s*([0-f]+)\s*([0-f]+)\s*([0-f]+)\s*([0-f]+)", output.decode("UTF-8")
    ).group(2)

    out = int(line, 16)
    return out


def round_up(value, roundby):
    return -(-value // roundby) * roundby + roundby


def calculate_size(file, alignment) -> int:
    return round_up(file.stat().st_size, alignment), file


def running_total(sizes, start):
    last = start
    ret = {}
    for k, (v, p) in sizes.items():
        ret[k] = last, p
        last = v + last
    return ret


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="output filename", type=Path)
    parser.add_argument(
        "-l", "--linux", help="path to Linux kernel", type=Path, required=True
    )
    parser.add_argument(
        "-i", "--initrd", help="path to initramfs", type=Path, required=True
    )
    parser.add_argument(
        "-r", "--osrel", help="path to os-release", type=Path, required=True
    )
    parser.add_argument(
        "-s", "--splash", help="path to splash image (.bmp format)", type=Path
    )
    parser.add_argument("-c", "--cmdline", help="cmdline string", type=str, default="")
    parser.add_argument("-e", "--efistub", help="path to EFI boot stub")
    parser.add_argument(
        "-A",
        "--arch",
        help="architecture to guess EFI stub with (x64, ia32, aa64...)",
        default=platform.machine(),
    )

    args = parser.parse_args()

    # use args.efistub as first priority, else guess the efistub.
    efistub = args.efistub if args.efistub is not None else guess_efistub(args.arch)

    with tempfile.NamedTemporaryFile() as cmdline:
        cmdline.write(f"{args.cmdline}".encode("UTF-8"))
        cmdline.seek(0)

        last_stub_section = parse_last_section(efistub)
        # close enough.
        alignment = 0x1000

        aligned_stub_section = round_up(last_stub_section, alignment)

        print(f"final stub section is at 0x{last_stub_section:x}")
        print(f"next section will be at 0x{aligned_stub_section:x}")

        # dicts are ordered in Python 3.7+.
        sizes = {}
        sizes[".osrel"] = calculate_size(args.osrel, alignment)
        sizes[".initrd"] = calculate_size(args.initrd, alignment)

        if args.splash is not None:
            sizes[".splash"] = calculate_size(args.splash, alignment)
        if args.cmdline != "":
            sizes[".cmdline"] = calculate_size(Path(cmdline.name), alignment)

        sizes[".linux"] = calculate_size(args.linux, alignment)

        print("sizes:")
        for k, (v, p) in sizes.items():
            print(f"{k}: 0x{v:x} at {p}")

        offsets = running_total(sizes, aligned_stub_section)

        print("offsets:")
        for k, (v, p) in offsets.items():
            print(f"{k}: 0x{v:x} at {p}")

        command_line = ["objcopy", str(efistub), str(args.output)]

        append = []
        for k, (v, p) in offsets.items():
            append += [
                "--add-section",
                f"{k}={p}",
                "--change-section-vma",
                f"{k}=0x{v:x}",
            ]

        command_line += append

        subprocess.run(command_line, check=False)


if __name__ == "__main__":
    main()
