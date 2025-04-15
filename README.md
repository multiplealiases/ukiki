# ukiki

Make UKIs using `objcopy`; a minimal subset of `ukify`.

## Dependencies

* An EFI stub from either systemd-boot or gummiboot
  (either installed or copied into the current working directory)

* `objdump`, `objcopy` (usually packaged as `binutils`):
   used to read off information about the EFI stub,
   then to append sections to the EFI stub

* Python 3.9

## Usage

```
usage: ukiki [-h] -l LINUX -i INITRD -r OSREL [-s SPLASH] [-c CMDLINE] [-e EFISTUB] [-A ARCH] output
ukiki.py: error: the following arguments are required: output, -l/--linux, -i/--initrd, -r/--osrel
```

While you don't strictly need an os-release (`-r/--osrel`)
to build a UKI, systemd-boot (and possibly rEFInd?)
won't accept a UKI without an `.osrel` section.

If you're in need of an os-release and `/etc/os-release` won't do,
the following should suffice as a template.

```
NAME=ook!
ID=ukiki
PRETTY_NAME=ook!
```

Refer to
[os-release(5)](https://www.man7.org/linux/man-pages/man5/os-release.5.html)
for more information.

## Installation

`./src/ukiki.py` is a self-contained Python script
that only depends on the stdlib, so you can copy it to anywhere in PATH.

You can also use `pipx` to install.

## Secure Boot

Out of scope because external tools do this better.
You can use `sbsign` to sign the generated UKI with
the same key/cert you use to sign your kernel normally.

```console
$ sbsign --key /etc/mok.key --cert /etc/mok.crt uki.efi --output uki.signed.efi
```

## A note on --splash

As far as I've been told
[bootsplash is a to-do feature](https://github.com/torvalds/linux/blob/8ffd015db85fea3e15a77027fda6c02ced4d2444/Documentation/gpu/todo.rst#bootsplash)
and will have no effect right now (as of kernel 6.14).
