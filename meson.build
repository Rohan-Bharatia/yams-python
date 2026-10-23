project(
  'yams',
  'cpp',
  version: '0.1.0',
  license: 'LGPL-3.0-or-later',
  default_options: [
    'warning_level=1',
    'cpp_std=c++23',
    'b_colorout=auto',
    'optimization=2',
    'b_pie=true',
  ],
)

fs = import('fs')

#
# WPILib native dependencies
#
# The headers and the static libraries are fetched by
# ``tools/fetch_native_deps.py`` (driven by the ``native`` hatch build hook)
# into the ``native/`` directory of the source tree.
#

wpilib_prefix = meson.current_source_dir() / 'native'
wpilib_include = wpilib_prefix / 'include'
wpilib_libdir = wpilib_prefix / 'lib'

if not fs.is_dir(wpilib_include) or not fs.is_dir(wpilib_libdir)
  error(
    'the WPILib native dependencies are missing; run ' +
    '"python tools/fetch_native_deps.py" before building',
  )
endif

yams_native_dep = declare_dependency(
  include_directories: include_directories('native/include'),
  link_args: [
    '-L' + wpilib_libdir,
    '-Wl,--start-group',
    '-lwpiutil',
    '-lwpimath',
    '-lwpinet',
    '-lntcore',
    '-ldatalog',
    '-lwpiHal',
    '-lwpilibc',
    '-lcommandsv2',
    '-ltelemetry',
    '-ltunables',
    '-Wl,--end-group',
    '-lpthread',
    # Statically link the C++ runtime so the wheel does not depend on the
    # exact libstdc++/libgcc versions of the machine that built it.
    '-static-libstdc++',
    '-static-libgcc',
  ],
)

#
# The YAMS C++ library
#
# The vendor specific motor controller wrappers (CTRE TalonFX/TalonFXS, REV
# Spark Max, ThriftyLib Nova) are not built: they need vendor libraries that
# are not redistributable.
#

yams_cpp_sources = files(
  'vendor/YAMS/yams/cpp/src/yams/gearing/GearBox.cpp',
  'vendor/YAMS/yams/cpp/src/yams/gearing/MechanismGearing.cpp',
  'vendor/YAMS/yams/cpp/src/yams/gearing/Sprocket.cpp',
  'vendor/YAMS/yams/cpp/src/yams/math/DerivativeTimeFilter.cpp',
  'vendor/YAMS/yams/cpp/src/yams/math/LQRConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/math/LQRController.cpp',
  'vendor/YAMS/yams/cpp/src/yams/math/SmartMath.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/SmartMechanism.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/config/ArmConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/config/ElevatorConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/config/FlyWheelConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/config/PivotConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/config/SimSensorConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/config/SwerveModuleConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/positional/Arm.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/positional/Elevator.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/positional/Pivot.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/positional/SmartPositionalMechanism.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/velocity/FlyWheel.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/velocity/SmartVelocityMechanism.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/swerve/SwerveDrive.cpp',
  'vendor/YAMS/yams/cpp/src/yams/mechanisms/swerve/SwerveModule.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/SmartMotorController.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/SmartMotorControllerConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/SmartMotorControllerCommandRegistry.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/simulation/ArmSimSupplier.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/simulation/BatterySim.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/simulation/DCMotorSimSupplier.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/simulation/ElevatorSimSupplier.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/simulation/Sensor.cpp',
  'vendor/YAMS/yams/cpp/src/yams/motorcontrollers/simulation/SensorData.cpp',
  'vendor/YAMS/yams/cpp/src/yams/telemetry/MechanismTelemetry.cpp',
  'vendor/YAMS/yams/cpp/src/yams/telemetry/SmartMotorControllerTelemetry.cpp',
  'vendor/YAMS/yams/cpp/src/yams/telemetry/SmartMotorControllerTelemetryConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/telemetry/SwerveDriveTelemetry.cpp',
  'vendor/YAMS/yams/cpp/src/yams/telemetry/SwerveDriveTelemetryConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/telemetry/SwerveModuleTelemetry.cpp',
  'vendor/YAMS/yams/cpp/src/yams/telemetry/SwerveModuleTelemetryConfig.cpp',
  'vendor/YAMS/yams/cpp/src/yams/units/EasyCRT.cpp',
)

#
# Semiwrap generates the pybind11 wrappers and the extension module.
#

subdir('semiwrap')

# Re-create the python installation with ``pure: false`` so that the extension
# module is installed into the ``platlib`` directory of the wheel.
sw_py = import('python').find_installation(pure: false)

yams_sources += yams_cpp_sources
yams_sources += files(
  'cpp/src/main.cpp',
  'cpp/src/SimMotorController.cpp',
)

yams_deps += declare_dependency(
  include_directories: include_directories(
    'vendor/YAMS/yams/cpp/include',
    'cpp/include',
  ),
)

yams_deps += yams_native_dep

# NOTE: the Python sources of the package (``yams/__init__.py`` and
# ``yams/py.typed``) are *not* installed here.  hatch-meson copies everything
# that meson installs into the package directory and force-includes it into
# the wheel; installing the python files as well would add them to the wheel
# twice.

subdir('semiwrap/modules')


# Vendor motor controller dependencies (optional)
# CTRE Phoenix 6, REVLib, ThriftyLib may be provided by environment
vendor_deps = []
# Try to find libraries if compiler is available
compiler = meson.get_compiler('cpp')
foreach libname : ['CTRE_Phoenix6', 'CTRE_Phoenix', 'REVLib', 'REV', 'ThriftyLib', 'thriftylib']
  l = compiler.find_library(libname, required : false)
  if l.found()
    vendor_deps += l
  endif
endforeach


# Add native vendor include dirs if present
if run_command('test', '-d', 'native/include', check: false).returncode() == 0
  yams_deps += declare_dependency(include_directories: include_directories('native/include'))
endif
