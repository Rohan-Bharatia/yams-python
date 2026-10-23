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

Semi-wrap 0.7.2 calls `pybind11-stubgen` with
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

Only the Linux x86-64 WPILib archives are pinned. Building on another platform
currently requires adding checksums for the corresponding artifacts and
verifying them; the script deliberately refuses to download unverified
archives.

## Compiler errors about C++23 or missing `std::` features

Use a C++23-capable compiler and make sure the project is configured with
`-std=c++23`. GCC 13+ or Clang 17+ is recommended. WPILib 2027 is the pinned
dependency stack; older WPILib headers are not supported.

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


## Cross-platform builds

- On macOS, ensure Xcode command line tools are installed
- On Windows, use Visual Studio Build Tools with C++ support
- For aarch64 Linux, set `YAMS_WPILIB_PLATFORM=linuxarm64` if auto-detection fails
- Vendor motor controllers require their respective libraries to be installed in the library path
