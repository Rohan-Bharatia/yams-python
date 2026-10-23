# Installation

## Supported platforms

| Platform | Status |
| --- | --- |
| Linux x86-64 | Built and tested locally and in CI |
| Linux aarch64 | Not supported by the pinned native-dependency checksums |
| macOS | Not built or verified |
| Windows | Not built or verified |

The extension links the WPILib C++ libraries statically and is compiled with
C++23. Python 3.9 or newer is declared, but the wheel and test suite have been
verified with CPython 3.14 locally and CPython 3.12 in CI. Other CPython
versions should work when building from source, but have not been verified.

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

- Linux x86-64
- CPython 3.9+ with development headers
- A C++23-capable compiler (GCC 13+ or Clang 17+ recommended)
- Meson and Ninja
- `objcopy` from binutils (optional; used to strip debug info from the static
  WPILib archives)
- `patchelf` (installed as a build dependency; used to remove absolute RPATHs
  from the wheel)

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
python -m pip install build "semiwrap==0.7.2" "hatch-meson>=0.1.3" \
    "hatchling>=1.27" "patchelf; sys_platform == 'linux'" \
    pybind11 "pybind11-stubgen>=2.5" meson ninja
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

The symlink is only needed for development; it is excluded from wheels.

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
| pybind11-stubgen | build dependency | Generates the wheel's `.pyi` stubs |
| Semi-wrap | 0.7.2 | Build-time code generator |
| Meson / Ninja | current stable | Build system |

The checksums in `tools/fetch_native_deps.py` currently cover the Linux x86-64
WPILib artifacts. Other platforms fail with an explicit error instead of
silently downloading unverified archives.

## License

The project is distributed under LGPL-3.0-or-later, matching YAMS. See
`LICENSE` and `THIRD_PARTY_NOTICES.md`.


## Supported platforms and Python versions

- **Platforms**: Linux x86_64, Linux aarch64, macOS (x86_64/arm64 universal), Windows x86_64
- **Python**: 3.12, 3.13, 3.14
