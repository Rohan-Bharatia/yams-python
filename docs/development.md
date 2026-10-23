# Development

## Repository layout

```text
.
├── cpp/
│   ├── include/yams/python/   # Hand-written adapters and type casters
│   └── src/                   # Extension entry point and adapters
├── semiwrap/                  # Semi-wrap YAML configuration
├── vendor/YAMS/               # YAMS submodule (v2026.10.19)
├── vendor/semiwrap/           # Semi-wrap submodule (0.7.2)
├── tools/fetch_native_deps.py # Pinned WPILib downloader
├── yams/                      # Python package (generated imports)
├── tests/                     # pytest suite
├── docs/                      # User and developer documentation
└── examples/                  # Runnable examples
```

Generated Meson files (`semiwrap/meson.build`, `semiwrap/modules/meson.build`
and `semiwrap/trampolines/meson.build`) are ignored by `semiwrap/.gitignore`.
They are produced by the Semi-wrap build hook from the YAML configuration; a
clean checkout does not need them.

## Submodules

```bash
git submodule update --init --recursive
```

| Submodule | Commit / tag |
| --- | --- |
| `vendor/YAMS` | `48085344887361058a25661aea57031cedea0d21` (`v2026.10.19`) |
| `vendor/semiwrap` | `b3cccdb82882bf0dffc6862fb60d939bc89547fa` (`0.7.2`) |

Do not edit files inside the submodules. Project-specific C++ code belongs in
`cpp/`; Semi-wrap customizations belong in `semiwrap/*.yml`.

## Architecture

1. `pyproject.toml` selects the `hatchling` build backend and three build hooks:
   - `custom` (`hatch_build.py`): fetches WPILib, strips RPATHs, and generates
     type stubs after the wheel is assembled.
   - `semiwrap`: parses the headers and generates pybind11 wrappers,
     trampolines, and Meson targets.
   - `meson`: compiles the extension with Ninja.
2. Semi-wrap generates `yams/_yams` from the headers listed in
   `[tool.semiwrap.extension_modules."yams._yams".headers]`.
3. `cpp/src/main.cpp` calls `initWrapper(m)` and adds bindings that Semi-wrap
   does not generate: the WPILib `SubsystemBase`, our `SimSubsystem`, and
   Python exception translations.
4. `meson.build` compiles the upstream YAMS sources selected for the binding
   and links the WPILib static archives. Vendor motor-controller wrappers (CTRE,
   REV, ThriftyLib) are deliberately excluded.
5. The wheel contains `yams/`, the compiled `_yams` extension, Semi-wrap
   trampolines, and generated `.pyi` stubs.

## Semi-wrap workflow

The installed Semi-wrap version is 0.7.2. The YAML files under `semiwrap/` are
the source of truth for the bindings. After changing a YAML file or adding a
header, regenerate the Meson files from the repository root:

```bash
SEMIWRAP_SKIP_PYI=1 .venv/bin/python -c "
import pathlib, sys
sys.path.insert(0, 'vendor/semiwrap/src')
from semiwrap.render_meson import render_meson_to_file
root = pathlib.Path('.').resolve()
render_meson_to_file(
    root,
    root / 'semiwrap' / 'meson.build',
    root / 'semiwrap' / 'modules' / 'meson.build',
    root / 'semiwrap' / 'trampolines' / 'meson.build',
)
"
```

`SEMIWRAP_SKIP_PYI=1` must also be set for `ninja`/hatch when compiling, because
Semi-wrap's stub target uses an `--ignore-invalid-expressions` pattern that does
not match raw WPILib type names such as `wpi::math::Pose3d`. The hatch build
hook sets this variable automatically and generates stubs separately in
`finalize`.

Then build:

```bash
ninja -C builddir
```

Semi-wrap reads YAML options such as `ignore`, `base_qualnames`,
`ignored_bases`, `force_no_trampoline`, `cpp_code`, `return_value_policy`,
`extra_includes`, and `extra_includes_first`. Unsupported declarations are
ignored in YAML and the reason is documented in the YAML comment or commit
history.

### Custom bindings and workarounds

- `std::initializer_list` parameters:
  `GearBox`, `Sprocket`, `SmartMath`, and `LQRConfig` expose Python-list based
  helpers that call the real C++ constructors/methods. See
  `cpp/include/yams/python/il_helpers.hpp` and the `cpp_code` entries in
  `semiwrap/gearing.yml`, `sprocket.yml`, `smart_math.yml`, and
  `lqr_config.yml`.
- Unit types (`turn_t`, `degree_t`, `meter_t`, ...) are converted to/from
  Python floats by `cpp/include/yams/type_casters/units.hpp`.
- `SimMotorController` is a hand-written adapter around
  `SmartMotorController` for hardware-free simulation.
- `SimSubsystem` gives Python-created motor controllers a real
  `wpi::cmd::SubsystemBase` instance.
- Exceptions are ignored by Semi-wrap and registered with
  `py::register_exception` in `cpp/src/main.cpp` so that they derive from
  Python's `Exception`. Re-running `semiwrap update-init` regenerates
  `yams/__init__.py` without the exception names; add them back (or run the
  current build) before committing. The test suite checks that they import.

## Running tests

```bash
.venv/bin/python -m pytest -q
```

The tests exercise the real compiled extension. Simulation tests use
`SimMotorController` and call `mechanism.sim_iterate()`; calling
`smc.sim_iterate()` alone does not advance a mechanism.

## Building a wheel

```bash
python -m build --wheel
```

To make the wheel installable from PyPI, repair it for manylinux:

```bash
pip install auditwheel
auditwheel repair -w wheelhouse dist/*.whl
```

`auditwheel` requires a wheel built on a glibc no newer than the target
policy. CI builds on Ubuntu and repairs the wheel there.

## Regenerating type stubs

Stubs are produced automatically during wheel finalization. To inspect or
regenerate them manually:

```bash
pip install pybind11-stubgen
PYTHONPATH=builddir/semiwrap/modules:. python -m pybind11_stubgen \
    --ignore-invalid-expressions='.*' --exit-code -o stubs yams
```

The permissive pattern skips signatures containing raw C++ types while keeping
the rest of the stub useful. Stubs are distributed in the wheel; they are not
committed to the source tree.
