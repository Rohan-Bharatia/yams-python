# Installation

## Supported platforms

| Platform | Status |
| --- | --- |
| Linux x86-64 | Built and tested locally and in CI |
| Linux aarch64 | Not built or verified |
| macOS (Apple Silicon) | Covered by CI; not verified locally |
| Windows x86-64 | Covered by CI; not verified locally |

The macOS WPILib archives are universal (x86-64 and arm64), but CI builds on
the arm64 `macos-latest` runner, so the Intel slice is not tested separately.

The extension links the WPILib C++ libraries statically and is compiled with
C++23. Python 3.12 or newer is required; the wheel and test suite have been
verified with CPython 3.14 locally, and CI targets CPython 3.12, 3.13, and
3.14.

## Installing a wheel

```bash
pip install yams-0.1.0-cp314-cp314-linux_x86_64.whl
```

The project is not currently published on PyPI. A wheel produced on a newer
glibc is tagged `linux_x86_64`; use `auditwheel repair` (see
`docs/development.md`) to produce a `manylinux` wheel that can be uploaded to a
package index.

## Building from source

The build downloads the pinned WPILib 2027.0.0-alpha-7 headers and static
libraries from the WPILib Maven repository. Network access to
`frcmaven.wpi.edu` is required unless `native/` already contains those files.

### System requirements

- Linux x86-64, macOS (x86-64 or Apple Silicon), or Windows x86-64
- CPython 3.12+ with development headers
- A C++23-capable compiler: GCC 14+, Clang 17+ (with a standard library that
  provides `<print>`), or MSVC from Visual Studio 2022 (on Windows, the build
  must run from a `vcvars64.bat` environment so Meson finds `cl.exe`)
- Meson and Ninja
- `objcopy` from binutils (Linux only, optional; used to strip debug info from
  the static WPILib archives)
- `patchelf` (Linux only, installed as a build dependency; used to remove
  absolute RPATHs from the wheel)

A local virtual environment is recommended:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install build
python -m build --wheel
```

`python -m build` uses an isolated environment and installs the versions in
`[build-system].requires` automatically. To use the tools already installed in
your environment, add `--no-isolation` and install them explicitly:

```bash
python -m pip install build "semiwrap==0.8.1" "hatch-meson>=0.1.3" \
    "hatchling>=1.33.0" "patchelf; sys_platform == 'linux'" \
    pybind11 "pybind11-stubgen~=2.5.1" meson ninja
python -m build --wheel --no-isolation
```

The wheel is written to `dist/`.

### Editable development install

```bash
python -m pip install -e . --no-build-isolation
```

If you prefer to compile with Meson directly instead of through hatch:

```bash
python tools/fetch_native_deps.py --prefix native
meson setup builddir
ninja -C builddir
ln -sf "$PWD/builddir/semiwrap/modules/_yams"*.so yams/
PYTHONPATH=. python -c "import yams; print(yams.__all__)"
```

On Windows, run this from a `vcvars64.bat` environment, configure with
`meson setup builddir -Dcpp_std=c++latest`, and copy the extension with
`copy /y builddir\semiwrap\modules\_yams*.pyd yams\` instead of the symlink.

The symlink (or copied extension) is only needed for development; it is
excluded from wheels.

### Verifying the wheel in a clean environment

```bash
python -m venv /tmp/yams-test
/tmp/yams-test/bin/pip install dist/*.whl pytest
cd /tmp
/tmp/yams-test/bin/python -m pytest -q "$OLDPWD/tests"
```

## Native dependencies

| Dependency | Version | How it is obtained |
| --- | --- | --- |
| YAMS C++ | v2026.10.19 submodule | Built from source |
| WPILib C++ | 2027.0.0-alpha-7 | Downloaded with pinned SHA-256 checksums |
| pybind11 | build dependency | Header-only, compiled into the extension |
| pybind11-stubgen | 2.5.1 | Generates the wheel's `.pyi` stubs |
| Semi-wrap | 0.8.1 | Build-time code generator |
| Meson / Ninja | current stable | Build system |

The checksums in `tools/fetch_native_deps.py` cover the Linux x86-64/arm64,
macOS, and Windows x86-64 WPILib artifacts; a platform without pinned
checksums fails with an explicit error instead of silently downloading
unverified archives. The static archives are linked with the platform's native
toolchain: GNU ld on Linux, ld64 on macOS, and MSVC's linker on Windows.

## License

The project is distributed under LGPL-3.0-or-later, matching YAMS. See
`LICENSE` and `THIRD_PARTY_NOTICES.md`.
