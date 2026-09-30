# Experimental J414s Apple Studio Display fix

Enable the existing J416s (16-inch M2 Pro) Thunderbolt DisplayPort path on
J414s (14-inch M2 Pro). This is a narrow, experimental patch against
`iconidentify/aurora-linux` commit
`17cba00e43b94ba6b5c64be7cbe3db9234a41f84`.

**Exp2: three same-port reconnects passed at 5K/60 Hz.** Exp1 enabled the first
picture but failed on reconnect. Exp2 adds a narrow clear-swap timeout change;
the timeout warning was observed and the subsequent reconnect recovered.
This remains an experimental result on one machine, not a qualified daily-use fix.

**Do not unbind/rebind the Apple Thunderbolt controller to recover it.**
On the test machine, resetting the right-side `f01ac0000.cio` controller and
then reconnecting caused a kernel NULL-pointer oops in
`apple_cio_tbt_switch_set`, called from `cd321x_update_work` through
`typec_thunderbolt_switch_set`. The desktop survived, but the connection did
not recover. The reset likely exposed a driver lifetime bug; its exact cause
has not been established. Reboot rather than attempting further live resets.

Exp2 changes four files and retains that base's SEP, AVD and other fixes.
It is not the full [Aurora PR #46](https://github.com/aurora-silicon/linux/pull/46),
which inspired the model enablement. That PR includes additional routing,
dual-stream, clock and bandwidth changes and does not apply cleanly to this base.

## Hardware result — September 30, 2026

- Apple MacBook Pro 14-inch M2 Pro (2023), `apple,j414s` / `apple,t6020`.
- Arch Linux ARM / Omarchy 4.0.4, Limine, m1n1-aurora 1.6.1.aurora2-2.
- Apple Studio Display, direct Thunderbolt connection, no dock.
- Before: authorized Thunderbolt device, disconnected DRM connectors;
  DP tunnel timed out after approximately 12 seconds on both sides of the Mac.
- After: experimental kernel `7.1.12-j414s-dp-exp1+` booted;
  `USB-3` connected; driver selected 5120×2880 at 60 Hz; owner confirmed
  a working displayed picture after hot-plugging.
- SEP remained read-only (`xart_writes=0 provision_keybag=0`).

Relevant after-patch messages:

```text
display routed to Thunderbolt DP tunnel dpin0
Apple: DP tunnel paths up, not waiting for DPRX
dpin0: active handshake=0
dpin0: crossbar link up (dispext=0 atc=0x1)
```

With exp1, on subsequent reconnects, the display still enumerated and the driver reported
the DP tunnel routed and active, but DRM remained disconnected. Cross-port
reconnect also failed.

After a fresh boot into `7.1.12-j414s-dp-exp2+`, the owner confirmed an initial
picture and three successful same-port unplug/replug cycles. Kernel logs recorded
5120×2880 at 60 Hz after each reconnect, with no observed kernel oops or RTKit
crash report. During the second cycle, the new diagnostic fired:

```text
clear swap timed out (swap 0); not latching firmware crash
```

The following reconnect restored 5K/60 Hz. This supports the false crash-latch
hypothesis; it does not establish that all reconnect failures are resolved.
Exp2 cross-port reconnect and suspend/resume have not been tested.

Only one machine and one display were tested. Suspend/resume,
cold boot with the display connected, audio,
camera, brightness controls, dual monitors and docks have not been qualified.
PCIe-C still reports a missing m1n1 preinit handoff; this patch does not fix it.
The generic `device links to tunneled native ports are missing!` warning also
remained despite successful video. Do not treat its presence alone as failure.

## What changes

The patch adds J414s alongside existing J416s checks in:

- `drivers/thunderbolt/apple.c`: T602x DP IN handshake and tunnel callbacks.
- `drivers/phy/apple/atc.c`: existing T6020 tunnel pixel-clock sequence.
- `drivers/gpu/drm/apple/dcp.c`: tunnel pipeline preference and HPD/timeouts.

No register sequences or shared driver interfaces are changed. This is model
enablement of an existing implementation, not a claim of general M2 support.

Exp2 additionally changes `drivers/gpu/drm/apple/iomfb_template.c`: a clear-swap
timeout warns instead of setting `dcp->crashed`. The early return is retained;
actual RTKit crash handling still sets the crash flag. This follows the narrow
approach discussed in [Aurora PR #5](https://github.com/aurora-silicon/linux/pull/5)
(closed, unmerged), not that PR's complete patch.

`j414s-dp-exp2.patch` is cumulative against the exact base above. Apply it alone,
not on top of `j414s-dp-exp1.patch`. Exp1 remains available for comparison.

## Reproduce the build

Use a separate build directory on disk, not a small RAM-backed `/tmp`.
The test used GCC 16.1.1, Rust 1.98.1, rust-bindgen 0.73.2 and pahole 1.32.
Clang 22.1.8 was installed for bindgen. Kernel `rustavailable` passed.
Build dependencies include base-devel, bc, bison, flex, openssl, libelf,
pahole, cpio, git, clang, llvm, rust, rust-src and rust-bindgen.

```sh
git clone https://github.com/iconidentify/aurora-linux.git linux-j414s
cd linux-j414s
git checkout --detach 17cba00e43b94ba6b5c64be7cbe3db9234a41f84
git apply --check /path/to/j414s-dp-exp2.patch
git apply /path/to/j414s-dp-exp2.patch
git diff --check

# Start from the tested Aurora kernel's configuration.
# Running an unrelated kernel's configuration is not equivalent.
mkdir ../build-j414s
zcat /proc/config.gz > ../build-j414s/.config
scripts/config --file ../build-j414s/.config \
  --set-str LOCALVERSION '-j414s-dp-exp2' --disable LOCALVERSION_AUTO
make O=../build-j414s ARCH=arm64 olddefconfig
make O=../build-j414s ARCH=arm64 rustavailable
make O=../build-j414s ARCH=arm64 -j6 Image modules dtbs
make O=../build-j414s ARCH=arm64 kernelrelease
```

The dirty source tree can add a trailing `+`; use the actual `kernelrelease`
when installing modules. The full Image/modules/dtbs build and module symbol
validation passed on the test machine.

## Installation approach

This repository intentionally provides no automatic installer. Installation
depends on the boot layout and firmware tooling of the existing Mac install.

The tested setup retained the packaged Aurora kernel and m1n1, installed
experimental modules under their distinct release directory, and generated a
separate UKI using the existing Omarchy mkinitcpio hooks and root command line.
A separate Limine EFI entry selected the experimental UKI; the original Aurora
entry remained available as a fallback. It used the packaged Aurora device
trees in m1n1, since this patch changes no device trees.

Before installation, back up `/boot` including the EFI filesystem, current
modules and boot configuration. Root snapshots alone do not back up separate
boot/EFI filesystems. Ensure enough EFI space for another roughly 60 MiB UKI.
Keep a known-good boot entry and verify the embedded kernel version, initrd,
root command line and module vermagic before rebooting. Preserve SEP read-only
mode unless independently choosing to test enclave writes with recovery available.

Unpackaged experimental modules may be removed by kernel-modules cleanup when
booting another kernel. Keep staged copies. Limine regeneration may alter manual
entries; this experiment is not integrated with distribution updates.

## Provenance and license

Patch prepared with OpenAI Codex at the machine owner's request. Hardware outcome
was confirmed by the owner; no upstream endorsement or review is implied.
The patch modifies Linux GPL-2.0-only files and is distributed under GPL-2.0-only.
See the base kernel's [COPYING](https://github.com/iconidentify/aurora-linux/blob/17cba00e43b94ba6b5c64be7cbe3db9234a41f84/COPYING).
