<div align="center">

# YAMS Python Bindings

Python bindings for [YAMS (Yet Another Mechanism System)](https://github.com/Yet-Another-Software-Suite/YAMS),
built with [Semi-wrap](https://github.com/robotpy/semiwrap),
[pybind11](https://pybind11.readthedocs.io) and Meson.

</div>

## Overview

This project exposes the real YAMS C++ mechanism library to Python. It is not a
Python reimplementation: Semi-wrap parses the upstream headers, generates
pybind11 wrappers, and Meson compiles those wrappers together with the upstream
YAMS sources and the WPILib static libraries into a single extension module.

```python
import yams

motor_config = (
    yams.SmartMotorControllerConfig()
    .with_motor_gearing(10.0)
    .with_subsystem(yams.SimSubsystem("arm"))
    .with_starting_position(0.0)
)
motor = yams.SimMotorController(motor_config)

arm = yams.Arm(
    yams.ArmConfig()
    .with_arm_length(1.0)
    .with_min_angle(-90.0)
    .with_max_angle(90.0),
    motor,
)

motor.set_duty_cycle(0.5)
for _ in range(10):
    arm.sim_iterate()

print(arm.get_angle())  # degrees
```

The package is not currently published on PyPI. Build a wheel from this
repository (see below), or install a wheel produced by the CI workflow.

## What is exposed

- Mechanisms: `Arm`, `Elevator`, `Pivot`, `FlyWheel`, plus the
  `SmartMechanism` hierarchy.
- Motor-control configuration and simulation: `SmartMotorControllerConfig`,
  `SimMotorController`, `SimSubsystem`, simulation suppliers.
- Gearing and math: `GearBox`, `Sprocket`, `MechanismGearing`, `SmartMath`,
  `LQRConfig`, `LQRController`, `DerivativeTimeFilter`, `EasyCRT`.
- Configuration value types, enums, telemetry fields, and YAMS exceptions.

Vendor motor-controller wrappers (CTRE TalonFX/TalonFXS, REV Spark Max,
ThriftyLib Nova) are intentionally not included because they require
non-redistributable vendor libraries. Use `SimMotorController` for hardware-free
development, testing and simulation.

## Supported platforms

| Platform | Status |
| --- | --- |
| Linux x86-64 | Built, tested, and covered by CI |
| Linux aarch64 | Not supported by the pinned native-dependency checksums |
| macOS | Not built or verified |
| Windows | Not built or verified |

The build requires a C++23 compiler, Meson, Ninja, and network access to the
WPILib Maven repository the first time native dependencies are fetched.
CPython 3.9+ is declared; the wheel and tests have been verified with CPython
3.14 locally and CPython 3.12 in CI.

## Installation

### From a wheel

```bash
pip install yams-0.1.0-cp314-cp314-linux_x86_64.whl
```

Wheels built on this Nix host require that host's glibc. For distribution, use
a wheel produced by CI and repaired with `auditwheel` (see
[`docs/development.md`](docs/development.md)).

### From source

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip build
python -m build --wheel
pip install dist/*.whl
```

`python -m build` installs the pinned build requirements in an isolated
environment. To use the active environment instead:

```bash
python -m pip install build "semiwrap==0.7.2" "hatch-meson>=0.1.3" \
    "hatchling>=1.27" "patchelf; sys_platform == 'linux'" \
    pybind11 "pybind11-stubgen>=2.5" meson ninja
python -m build --wheel --no-isolation
```

The `custom` build hook downloads the pinned WPILib headers and static
libraries with SHA-256 verification. See
[`docs/installation.md`](docs/installation.md) for system requirements and a
clean-environment verification recipe.

### Editable development build

```bash
python -m pip install -e . --no-build-isolation
pytest
```

Alternatively compile with Meson directly:

```bash
python tools/fetch_native_deps.py --prefix native
meson setup builddir
ninja -C builddir
ln -sf "$PWD/builddir/semiwrap/modules/_yams"*.so yams/
PYTHONPATH=. python -c "import yams"
```

## Project architecture

```text
vendor/YAMS C++ headers + sources
        │
        ├── semiwrap/*.yml ──> generated pybind11 wrappers, trampolines, Meson
        │
cpp/ (adapters, type casters, module entry point)
        │
        └── Meson + Ninja ──> yams._yams extension ──> yams package ──> wheel
```

- `pyproject.toml` configures hatchling with three hooks: `custom`
  ([`hatch_build.py`](hatch_build.py)) fetches WPILib and polishes the wheel,
  `semiwrap` generates the bindings, and `meson` compiles the extension.
- `semiwrap/*.yml` is the source of truth for the exposed API.
- `cpp/` contains only binding glue: the `SimMotorController` adapter,
  `SimSubsystem`, unit type casters, and the `std::initializer_list` helper.
- `vendor/YAMS` is pinned to `v2026.10.19`
  (`48085344887361058a25661aea57031cedea0d21`); `vendor/semiwrap` is pinned to
  `0.7.2` (`b3cccdb82882bf0dffc6862fb60d939bc89547fa`).

More detail: [`docs/development.md`](docs/development.md).

## Usage notes

### Gearing helpers

C++ `std::initializer_list` methods accept Python sequences:

```python
gearbox = yams.GearBox.from_reduction_stages([10.0, 2.0])
gearbox = yams.GearBox.from_stages(["10:1", "2:1"])
gearbox = yams.GearBox.from_teeth([12, 36, 12, 36])
sprocket = yams.Sprocket.from_stages(["10:1", "2:1"])
```

### Units

Unit types are exposed as Python `float` values. The unit is part of each
method's documented meaning, not its Python type. See
[`docs/api.md`](docs/api.md) for the full API and unit conventions.

### Simulation

Mechanisms drive the simulated motor controller. Advance simulation with
`mechanism.sim_iterate()`; calling `smc.sim_iterate()` alone does not move the
mechanism. Closed-loop commands need configured gains and feedback. See
[`examples/simulated_arm.py`](examples/simulated_arm.py).

### Exceptions

All YAMS exceptions derive from `yams.YamsException`, which derives from
Python's `Exception`:

```python
try:
    yams.SmartMath.gear_box([])
except yams.NoStagesGivenException:
    ...
```

## Testing

```bash
.venv/bin/python -m pytest -q
```

The suite exercises the compiled extension: imports, configuration builders,
gearing and type conversion, enum values, simulated mechanisms, exceptions,
encoder state, and absolute-encoder solving. Tests do not use hardware or
vendor libraries.

## Documentation

- [`docs/installation.md`](docs/installation.md) — platforms, prerequisites,
  source builds, clean-environment wheel verification.
- [`docs/development.md`](docs/development.md) — submodules, Semi-wrap YAML
  workflow, Meson integration, custom bindings, stub generation.
- [`docs/api.md`](docs/api.md) — exported classes, methods, units, ownership,
  and limitations.
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — build, linker, RPATH,
  auditwheel, import, and simulation problems.
- [`examples/simulated_arm.py`](examples/simulated_arm.py) — verified
  hardware-free example.

## Known limitations

- Vendor hardware controllers are not bound.
- Only Linux x86-64 is built and tested.
- `to_robot_attitude` takes a WPILib `Rotation3d`, which this project does not
  bind, so it is only usable with a value produced by another extension.
- `SmartMotorControllerTelemetryConfig` is not bound because it is
  non-copyable and libstdc++ incorrectly reports it as copy-constructible.
- Unit overloads that differ only by unit cannot be distinguished from Python
  and resolve in declaration order.
- Semi-wrap's built-in stub step is disabled; the hatch build generates stubs
  separately with a permissive `pybind11-stubgen` invocation.

## License

The bindings are distributed under LGPL-3.0-or-later, matching YAMS. See
[`LICENSE`](LICENSE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for
WPILib, pybind11, and Semi-wrap attribution.

## Links

- [YAMS upstream](https://github.com/Yet-Another-Software-Suite/YAMS)
- [Semi-wrap](https://github.com/robotpy/semiwrap) /
  [documentation](https://semiwrap.readthedocs.io/en/latest/)
- [pybind11](https://pybind11.readthedocs.io)
- [WPILib](https://docs.wpilib.org)


## Cross-platform support

- **Linux x86_64, Linux aarch64**: Supported via WPILib static libraries
- **macOS (Intel/Apple Silicon, osxuniversal)**: Supported via WPILib universal static libraries  
- **Windows (x86_64)**: Supported via WPILib static libraries

Python versions 3.12, 3.13, and 3.14 are supported. Use `YAMS_WPILIB_PLATFORM` to override platform detection if needed.

## Vendor motor controllers

The following vendor motor controllers are supported via their native libraries:

- **CTRE Phoenix 6** (TalonFX, TalonFXS) - via `ctre::phoenix6` API
- **REV Robotics** (SPARK MAX, SPARK Flex) - via `rev` API  
- **ThriftyBot ThriftyLib/Nova** - via `thrifty` API

These require the respective vendor libraries to be installed. See the YAMS documentation for details.
