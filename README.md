# Experimental J414s Apple Studio Display fix

Enable the existing J416s (16-inch M2 Pro) Thunderbolt DisplayPort path on
J414s (14-inch M2 Pro). This is a narrow, experimental patch against
`iconidentify/aurora-linux` commit
`17cba00e43b94ba6b5c64be7cbe3db9234a41f84`.

**Exp2: three same-port reconnects passed at 5K/60 Hz.** Exp1 enabled the first
picture but failed on reconnect. Exp2 adds a narrow clear-swap timeout change;
the timeout warning was observed and the subsequent reconnect recovered.
This remains an experimental result on one machine, not a qualified daily-use fix.

**Latest status (October 2, 2026): local exp5 booted with tunneled USB, but
physical brightness remains unresolved.** A working x86 ThinkPad Nano now gives
us a comparison baseline: its brightness USB payloads match ARM, while its
reported video configuration differs. See the [current investigation and next
tests](TESTING-2026-10-02.md), and the [September 30 history](TESTING-2026-09-30.md).
The published patches below stop at exp3; local exp4/exp5 changes have not yet
been packaged here. Exp5 reconnect and suspend/resume are not qualified.
Successful HID readback is not proof of physical backlight control, and the
video-depth difference is a candidate, not a confirmed cause.

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
The owner then moved the connection to the opposite side of the Mac and
confirmed a working picture. Logs showed the `f01f00000.nhi` controller's DP
tunnel up, `USB-3` connected, and 5120×2880 at 60 Hz again, with no new observed
kernel oops or RTKit crash report. This is one successful cross-side move.

The owner also reported charging working at **65 W** with the display connected.
This is an owner-reported result, not an independently measured USB-PD contract
or sustained battery charging-rate measurement.

Exp2 suspend/resume has not been tested.

### Desktop layout and brightness follow-up

Omarchy Hyprmoncfg plugin 2.7.0 with the ARM64 hyprmoncfg 1.22.0 backend was
installed and enabled. Both displays were detected, and the following stacked
layout was applied, validated with no Hyprland configuration errors, and saved
as `studio-above-laptop`:

| Display | Mode | Scale | Logical position |
| --- | --- | --- | --- |
| Studio Display | 5120×2880 at 60 Hz | 2 | 0×0 |
| Laptop (`eDP-1`) | 3024×1890 at 120 Hz | 1.75 | 416×1440 |

This centers the laptop directly below the Studio Display. The Studio Display
rule uses its display description rather than `USB-3`, so the rule is not tied
to that port's connector name. These are desktop configuration results, not
additional kernel changes; the saved profile is local to the test machine.

The following paragraph records the **earlier exp2 state**, superseded by the
exp4 USB results in the [test log](TESTING-2026-09-30.md).
Hardware brightness control remained unavailable in that test. Omarchy's
`asdcontrol` query found no Apple Display HID device; the enumerated hidraw
devices were the laptop's internal inputs. Privileged `ddcutil detect` found no
displays. The display's audio device was also absent from the ALSA card list.
`USB-3` is a DRM display-connector label, not proof that USB peripherals have
enumerated. No brightness change or live controller reset was attempted.

[asdcontrol issue #5](https://github.com/nikosdion-archive/asdcontrol/issues/5)
describes the same video-without-USB-control shape: brightness uses USB HID,
not DisplayPort DDC. [Aurora PR #50](https://github.com/aurora-silicon/linux/pull/50)
is a relevant candidate for the missing PCIe-C preinit handoff
reported on this machine. Its PCIe-C/USB results were tested on J416c M2 Max,
not this J414s M2 Pro; it has not been qualified here.

### Exp3 PCIe-C preflight — historical build and installation record

A diagnostic m1n1 build successfully booted this J414s with the working exp2
kernel. It exported `dart-tunables-instance-0` from this machine's actual iBoot
ADT for all three `dart-apciec` ports. All three sets matched PR #50's J416c
reference exactly:

```text
<0x20c 0xff0000b7 0xe40000b7>
<0x220 0x000f0f0f 0x000f0f0f>
<0x224 0x00ffffff 0x00080808>
<0x300 0x00001f31 0x00000001>
<0x308 0x3ffffffc 0x10000000>
<0x310 0x3ffffffc 0x3ffffffc>
```

`m1n1-j414s-dart-diagnostic.patch` targets
`iconidentify/m1n1` / `aurora-silicon/m1n1` commit
`97e2de3d4fec0ea707691fecf7772efce664ca5e`. It copies raw ADT properties under
diagnostic names in `/chosen`; it does not enable PCIe-C, create driver-consumed
tunable properties, or apply those values to MMIO. Missing/malformed data is
reported without intentionally blocking boot. `decode-dart-diagnostic.py`
decodes the exported little-endian records and checks access size, alignment,
offset bounds and 32-bit masks/values. The diagnostic bootloader was installed
with the previous exact stage-2 bundle backed up; DTB and U-Boot payloads were
verified unchanged. This successful boot is not a PCIe-C or brightness test.

`j414s-pcie-exp3.patch` is a **cumulative candidate against the same Linux base
as exp2**, applied alone, not on top of exp2. It retains exp2's video changes and
ports the narrow PCIe-C idea instead of PR #50's full stacked display series:

- J414s-only `apple,j414s-pciec-exp3` DT flags and independently verified DART
  tunables. Older exp2/package kernels ignore this experiment-specific flag,
  avoiding unintended cold initialization when selecting a fallback kernel.
- Default-off `pcie_apple.tunnel_kernel_init` opt-in, guarded before activation.
- Early M2 preparation maps Intr2AXI rather than requiring M1's OE-fabric region.
- Cold init waits for RUN before root-complex register accesses, then configures
  the bridge and clears RID mappings; the original M1 path remains separate.
- No connector renaming or new dual-stream routing changes.

The touched PCIe/Thunderbolt objects and J414s DTB compiled with `W=1`.
The compiled DTB's tunables and flags were inspected on all three ports;
`git diff --check` passed. Checkpatch reports zero errors and one packaging
warning because the cumulative patch combines DT bindings and driver changes. Existing
device-tree warnings and a Rust unused-import warning were present. The full
Image/modules/dtbs build passed, including module symbol validation. A final
rebuild with the fallback-safe DT flag also passed.

**At the time of this pre-reboot record, exp3 was installed but not boot-tested.**
It subsequently failed to probe because of an M1-only OE-fabric resource check;
the local exp4 correction and its hardware results are documented in the
[test log](TESTING-2026-09-30.md). The remainder of this section preserves the
original preflight record rather than describing the currently running kernel.
The separate UKI selects `7.1.12-j414s-pcie-exp3+` with
`pcie_apple.tunnel_kernel_init=1`. Its matching modules and boot command line
were verified. The m1n1 bundle replaces exactly one J414s DTB; every other
packaged DTB is unchanged. The exact previous bundle is retained as
`boot.bin.pre-exp3`, alongside an additional workspace backup. Correct
DART values remove one uncertainty, not the cold-init/teardown/resume risks.
At that point the running kernel remained exp2 until reboot. The older exp2 and
packaged Aurora boot entries remain available and ignore exp3's custom flag.
Selecting an older Limine kernel does not restore the shared device tree;
restore the exact stage-2 backup for a complete rollback. Preserve exact
stage-2 backups and a recovery route before any activation. Do not perform
live controller resets. No additional upstream PR has been opened.

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
