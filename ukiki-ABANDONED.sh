#!/usr/bin/env sh

set -o nounset
set -o errexit

# ukiki: generate UKI images using objcopy

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

die() {
	# shellcheck disable=SC2059
	printf "$@"
	exit 1
}

info() {
    1>&2 printf '>>> %s\n' "$1"
}

help(){
    cat << EOF
ukiki: generate UKI images using objcopy
Usage: ukiki --linux [linux] --initrd [initrd] --osrel [osrel] --output [name]
Options
-l, --linux     path to Linux kernel (required)
-i, --initrd    path to initrd (required)
-r, --osrel     path to os-release (required)
-c, --cmdline   cmdline string
-s, --splash    path to splash .bmp
-e, --efistub   path to EFI stub
-o, --output    output file prefix (required)
-h, --help      this help
EOF
}

cleanup_array="$(mktemp)"
cleanup() {
    < "$cleanup_array" xargs -0 -I{} rm -rf {}
    rm -f "$cleanup_array"
}
# shellcheck disable=SC2120
append_mktemp() {
    tmp="$(mktemp "$@")"
    printf "%s\0" "$tmp" >> "$cleanup_array"
    printf "%s\n" "$tmp"
}
trap 'cleanup' INT HUP TERM EXIT

guess_efistub() {
    if [ -f /usr/lib/systemd/boot/efi/linuxx64.efi.stub ]
    then
        echo /usr/lib/systemd/boot/efi/linuxx64.efi.stub
    elif [ -f /usr/lib/gummiboot/linuxx64.efi.stub ]
    then
        echo /usr/lib/gummiboot/linuxx64.efi.stub
    else
        echo
    fi
}

efistub_candidate="$(guess_efistub)"
efistub="${efistub-$efistub_candidate}"
missing_efistub="no"

if [ "$efistub" = "" ]
then
    1>&2 cat << MSG
The EFI stub linuxx64.efi.stub (required to produce a UKI)
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

MSG
    missing_efistub="yes"
fi


if [ "$missing_efistub" = yes ]
then
    exit 1
fi



while [ "$#" -gt 0 ]
do
    case "$1" in
    --help)
        help
        exit 1
        ;;
    -o | --output)
        output="$2"
        shift 2
        ;;
    -l | --linux)
        linux="$2"
        shift 2
        ;;
    -r | --osrel)
        osrel="$2"
        shift 2
        ;;
    -i | --initrd)
        initrd="$2"
        shift 2
        ;;
    -s | --splash)
        splash="$2"
        shift 2
        ;;
    -c | --cmdline)
        cmdline="$2"
        shift 2
        ;;
    *)
        die "argument(s) not recognized: %s\nUse --help for help\n" "$*"
        ;;
    esac
done

info 'Generating UKI'
# Thank you, Arch Linux wiki.
# https://wiki.archlinux.org/title/Unified_kernel_image#Manually
align="$(objdump -p "$efistub" | awk '{ if ($1 == "SectionAlignment"){print $2} }')"
align=$(printf '%d\n' "$align")

osrel_offs="$(objdump -h "$efistub" | tail -n2 | head -n1 | tr -s ' ' | cut -f 4,5 -d ' ' | xargs printf '0x%s ' | xargs -n1 printf '%d ' | awk '{print $1 + $2}')"
osrel_offs=$((osrel_offs + align - osrel_offs % align))
# move the .osrel offset by 128 $aligns to appease the PE gods
osrel_offs=$((osrel_offs + 128 * align ))

initrd_offs=$((osrel_offs + $(stat -Lc%s "$osrel")))
initrd_offs=$((initrd_offs + align - initrd_offs % align))



# .linux must be the final section to allow in-place decompression.
linux_offs=$((initrd_offs + $(stat -Lc%s "$initfs")))
linux_offs=$((linux_offs + align - linux_offs % align))
