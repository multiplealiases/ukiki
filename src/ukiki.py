#!/usr/bin/env python3

from pathlib import Path
import sys
import argparse
import platform
import re

# This script requires Python 3.9.

# ukiki: make UKI using objcopy

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
Void: systemd-boot-efistub""")


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
    parser.add_argument("-c", "--cmdline", help="cmdline string", type=str)
    parser.add_argument("-e", "--efistub", help="path to EFI boot stub")
    parser.add_argument(
        "-A",
        "--arch",
        help="architecture to guess EFI stub with (x64, ia32, aa64...)",
        default=platform.machine(),
    )

    args = parser.parse_args()

    print(args)

    # use args.efistub as first priority, else guess the efistub.
    efistub = args.efistub if args.efistub is not None else guess_efistub(args.arch)

    print(f"guessed efistub {efistub}")


if __name__ == "__main__":
    main()
