# Troubleshooting

## `ImportError: cannot import name '_yams' from 'yams'`

The native extension was not built or was not copied next to `yams/__init__.py`.

For a development build:

```bash
ls builddir/semiwrap/modules/_yams*.so
ln -sf "$PWD/builddir/semiwrap/modules/_yams"*.so yams/
PYTHONPATH=. python -c "import yams"
```

For an installed wheel, reinstall it:

```bash
pip install --force-reinstall dist/*.whl
```

## `ModuleNotFoundError: No module named 'yams'` when running an example

Running `python examples/simulated_arm.py` puts `examples/`, not the repository
root, on `sys.path`. Install the wheel, or run:

```bash
PYTHONPATH=. python examples/simulated_arm.py
```

## `ninja: error: 'pyproject.toml', needed by ..., missing and no known rule to make it`

Semi-wrap's Meson renderer was run from the wrong directory, producing relative
paths based on the build directory. Re-render from the repository root:

```bash
SEMIWRAP_SKIP_PYI=1 .venv/bin/python -c "
import pathlib, sys
sys.path.insert(0, 'vendor/semiwrap/src')
from semiwrap.render_meson import render_meson_to_file
root = pathlib.Path('.').resolve()
render_meson_to_file(root, root/'semiwrap'/'meson.build',
                     root/'semiwrap'/'modules'/'meson.build',
                     root/'semiwrap'/'trampolines'/'meson.build')
"
```

## Stub generation aborts with `Invalid expression 'wpi::...'`

Semi-wrap calls `pybind11-stubgen` with
`--ignore-invalid-expressions=<.*>`, which does not match C++ type names in
pybind11 docstrings. Keep `SEMIWRAP_SKIP_PYI=1` set while rendering and
compiling. The hatch build hook sets it automatically and generates stubs in
`finalize` with a permissive pattern.

## `TypeError: ... std::vector<double> ... Did you forget to #include <pybind11/stl.h>?`

A `std::vector` only appears in a `cpp_code` expression, so Semi-wrap's parser
does not add the STL caster include. Add `pybind11/stl.h` through
`extra_includes` in the relevant YAML file (already done for the gearing and
LQR helpers).

## `TypeError: ... (type not registered yet?)` for unit types

The extension module must include its own exported casters through the
`depends = ["yams_units"]` entry in
`[tool.semiwrap.extension_modules."yams._yams"]`. If unit arguments suddenly
fail to convert, verify that entry and that
`cpp/include/yams/type_casters/units.hpp` is included in the build.

## Missing WPILib headers or static libraries

```text
the WPILib native dependencies are missing; run
"python tools/fetch_native_deps.py" before building
```

Run:

```bash
python tools/fetch_native_deps.py --prefix native
```

The artifacts are pinned by SHA-256 in `tools/fetch_native_deps.py`. If a
download is corrupted, use `--force` to re-download everything.

## `no pinned checksums for platform tag ...`

The WPILib archives are pinned for Linux x86-64/arm64, macOS (universal), and
Windows x86-64. Building on another platform (for example Windows ARM64)
requires adding checksums for the corresponding artifacts and verifying them;
the script deliberately refuses to download unverified archives.

## Compiler errors about C++23 or missing `std::` features

Use a C++23-capable compiler: GCC 14+, Clang 17+ with a standard library that
provides `<print>`, or a current Visual Studio 2022. WPILib's headers include
`<print>` unconditionally, and libstdc++ only ships that header from GCC 14;
Ubuntu 24.04 therefore needs `g++-14` even though its default `c++` is GCC 13.
GCC and Clang are configured with `-std=c++23`; Meson's MSVC backend spells the
same language level `/std:c++latest`, which the hatch build selects
automatically through a generated native file. `meson.build` also passes
`/Zc:preprocessor` on MSVC because the WPILib headers use `__VA_OPT__`, which
the traditional MSVC preprocessor does not expand. If you configure Meson by
hand on Windows, pass the options explicitly:

```bat
meson setup builddir -Dcpp_std=c++latest
```

WPILib 2027 is the pinned dependency stack; older WPILib headers are not
supported.

## Linker errors mentioning `wpiutil`, `wpimath`, `commandsv2`, etc.

The WPILib static archives must all be present in `native/lib/`. Re-run the
fetch script. The link line groups the archives with `--start-group` /
`--end-group`, so library order should not be the problem; a missing archive or
an incomplete download usually is.

## `ImportError` / `libstdc++.so.6: version 'GLIBCXX_...' not found`

The extension statically links libstdc++ and libgcc, so a normal wheel should
not require a specific `libstdc++`. If you built an older revision without the
static link flags, rebuild with the current `meson.build`.

The local Nix-built wheel still requires the glibc version of the build host
(it references symbols up to `GLIBC_2.38` and the Nix glibc adds
`GLIBC_ABI_GNU2_TLS`). Use a CI-built / manylinux wheel for distribution to
older systems.

## `auditwheel: cannot repair ... too-recent versioned symbols`

The wheel was linked against a newer glibc than the target manylinux policy.
Build in a manylinux container or on an older distribution, then run
`auditwheel repair` there. The GitHub Actions workflow builds on Ubuntu and
performs this step.

## `ValueError: Expected a BaseException type` when catching YAMS exceptions

This happened before exceptions were registered as Python exceptions. Current
builds register every YAMS exception with `py::register_exception`, so
`issubclass(yams.YamsException, Exception)` is true. If you regenerated
`yams/__init__.py` with `semiwrap update-init`, make sure the exception names
are still re-exported and rebuild the extension.

## Simulation does not advance

Call `mechanism.sim_iterate()`, not only `smc.sim_iterate()`. The mechanism is
responsible for feeding the simulated plant; the controller alone does not move
the mechanism.

Closed-loop commands also require configured PID/feedforward gains and a
feedback source. An open-loop `set_duty_cycle` is the simplest way to verify
that simulation is running.


## Platform-specific build problems

- **Windows: `cl.exe` not found / MSVC libraries not linked.** The runner or
  shell must activate Visual Studio first (`call vcvars64.bat`); otherwise
  Meson may pick another compiler and fail to link the MSVC `.lib` archives.
- **Windows: `unsupported platform` from `fetch_native_deps.py`.** 64-bit
  Windows reports its architecture as `AMD64`; the mapping is case-insensitive,
  so this only happens on an architecture without pinned archives (for example
  Windows ARM64).
- **macOS: linker errors about missing symbols.** macOS uses ld64, which reads
  the universal `.a` archives directly; no GNU linker groups are used. Make
  sure the native dependencies were fetched for `osxuniversal`.
- **Linux aarch64.** Archives are pinned for `linuxarm64`, but the platform is
  not built or tested in CI.
- **Overriding platform detection.** Set `YAMS_WPILIB_PLATFORM` to
  `linuxx86-64`, `linuxarm64`, `osxuniversal`, or `windowsx86-64` to select an
  archive set explicitly (for example when cross-compiling). The chosen tag
  must have pinned checksums.
- Platforms whose archives are not pinned in `CHECKSUMS` are rejected instead
  of being downloaded unverified.
