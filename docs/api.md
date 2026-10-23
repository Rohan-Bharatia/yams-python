# API reference

The public package is `yams`. Every name below is re-exported from the native
extension `yams._yams`. Type stubs (`.pyi`) are included in the wheel, so IDEs
and type checkers can discover the full signatures. `help(yams.Name)` also
shows the docstrings generated from the upstream C++ comments.

## Conventions

- Unit-typed C++ parameters and return values are exposed as Python `float`.
  This includes turns, degrees, radians, meters, seconds, volts, amperes and
  derived units. The unit is part of the method name or its documented meaning,
  not the Python type.
- Because `degree_t`, `radian_t` and `turn_t` all become `float`, overloads
  that differ only by unit are selected in declaration order. Prefer the
  explicitly named methods (for example `with_starting_position` where the unit
  is documented) and check behaviour when mixing units.
- C++ `std::optional<T>` is returned as `T | None`.
- `std::vector<T>` and `std::initializer_list<T>` parameters accept Python
  sequences/lists.
- Objects returned by reference (for example `get_config()`) keep their owner
  alive through pybind11's lifetime policies. Do not assume that a returned
  object can outlive the mechanism/controller that created it if the C++ API
  documents a non-owning pointer.
- Vendor motor-controller classes (CTRE, REV, ThriftyLib) are not bound. Use
  `SimMotorController` for hardware-free code.

## Exported names

```text
Arm, ArmConfig, ArmConfigurationException, ArmSimSupplier,
BooleanTelemetryField, DCMotorSimSupplier, DerivativeTimeFilter,
DoubleTelemetryField, EasyCRT, Elevator, ElevatorConfig,
ElevatorConfigurationException, ElevatorSimSupplier, FlyWheel,
FlyWheelConfig, GearBox, GyroAxis, InvalidStageGivenException, LQRConfig,
LQRController, MechanismGearing, MechanismPositionConfig, MechanismTelemetry,
NoStagesGivenException, Pivot, PivotConfig, PivotConfigurationException,
SimMotorController, SimSensorConfig, SimSubsystem, SimSupplier, SmartMath,
SmartMechanism, SmartMotorController, SmartMotorControllerConfig,
SmartMotorControllerConfigurationException, SmartMotorControllerTelemetry,
SmartPositionalMechanism, SmartVelocityMechanism, Sprocket, SubsystemBase,
SwerveDriveConfigurationException, UnsupportedTelemetryFields, YamsException,
to_robot_attitude
```

## Gearing and math

### `GearBox`

Input-to-output conversion factor for a multi-stage gearbox.

```python
GearBox(reduction_stage: float)
GearBox(reduction_stages: Sequence[float])
GearBox(stages: Sequence[str])

GearBox.from_reduction_stages(stages)
GearBox.from_stages(["10:1", "2:1"])
GearBox.from_teeth([12, 36, 12, 36])
```

Methods: `get_input_to_output_conversion_factor()`,
`get_output_to_input_conversion_factor()`, `times(ratio)`, `div(ratio)`.
`from_teeth` requires an even number of positive tooth counts.

### `Sprocket`

Same interface as `GearBox`, but for chain/belt stages. Methods include
`from_stages`, `times`, `div`, and the two conversion-factor getters.

### `MechanismGearing`

```python
MechanismGearing(reduction_ratio: float)
MechanismGearing(gear_box: GearBox)
MechanismGearing(gear_box: GearBox, sprockets: Sprocket)
```

Methods: `get_rotor_to_mechanism_ratio()`,
`get_mechanism_to_rotor_ratio()`, `div(value)`.

### `SmartMath`

Static helpers:

```python
SmartMath.gear_box([10.0, 2.0])                 # 20.0
SmartMath.sensor_to_mechanism_ratio([3.0, 4.0]) # 12.0
```

Raises `NoStagesGivenException` for an empty list.

### `LQRConfig` / `LQRController`

`LQRConfig` is a builder for LQR controllers:

```python
config = (
    LQRConfig()
    .with_q_elems([1.0, 2.0])
    .with_r_elems([12.0])
    .with_state_std_devs([0.1, 0.1])
    .with_measurement_std_devs([0.01])
)
```

Other builders: `with_period`, `with_max_voltage`, `with_type`, `with_arm_system`,
`with_elevator_system`, `with_flywheel_system`. `with_type` takes
`LQRConfig.LQRType.arm`, `.elevator`, or `.flywheel`.

`LQRController` methods: `calculate`, `reset`, `update_config`, `get_config`,
`get_type`.

### `DerivativeTimeFilter`

```python
DerivativeTimeFilter(initial: float, debouncer_period: float)
DerivativeTimeFilter(debouncer_period: float)
```

`derivative(current)` and `derivative(current, dt)` return the filtered
derivative.

### `EasyCRT`

```python
EasyCRT(shared_gear_teeth: int, encoder_a_teeth: int, encoder_b_teeth: int)
```

Methods: `get_unique_range() -> float`, `solve(encoder_a, encoder_b) -> float | None`.

## Configuration classes

All configuration classes are mutable builders whose `with_*` methods return
`self`, so calls can be chained.

### `ArmConfig`

`with_arm_length(meters)`, `with_min_angle(degrees)`,
`with_max_angle(degrees)`, `with_telemetry_name(name)`,
`with_sim_color(color)`, `with_mechanism_position_config(config)`.
Getters mirror the `with_*` names (`get_arm_length`, ...).

### `ElevatorConfig`

`with_minimum_height(meters)`, `with_maximum_height(meters)`,
`with_carriage_mass(kg)`, `with_stages(...)`, `with_angle(degrees)`,
`with_is_horizontal(bool)`, `with_telemetry_name(name)`, `with_sim_color`,
`with_mechanism_position_config`.

### `PivotConfig`

`with_min_angle`, `with_max_angle`, `with_telemetry_name`, `with_sim_color`,
`with_mechanism_position_config`.

### `FlyWheelConfig`

`with_roller_diameter(meters)`, `with_telemetry_name(name)`, `with_sim_color`,
`with_mechanism_position_config`.

### `MechanismPositionConfig`

Describes where a mechanism is mounted and how it moves:
`with_relative_position`, `with_movement_plane`, `with_parent`,
`get_mount_pose`, `get_relative_position`, `get_movement_plane`,
`get_rotated_pose`, `get_translated_pose`, `rotation_in_plane`.
Planes: `MechanismPositionConfig.Plane.xz`, `.yz`, `.xy`.

### `SimSensorConfig`

Builder for simulated sensors: `with_field(name, value)`,
`with_simulated_value(value)`, `get_fields`, `get_name`, `get_sensor`.

### `SmartMotorControllerConfig`

The main controller configuration builder. Important methods:

- Gearing and feedback: `with_motor_gearing`, `with_external_encoder`,
  `with_external_encoder_gearing`, `with_external_encoder_inverted`,
  `with_feedback(kP, kI, kD, slot=...)`,
  `with_feedback_synchronization_threshold`,
  `with_use_external_feedback_encoder`.
- Closed/open loop: `with_closed_loop_mode`, `with_open_loop_mode`,
  `with_closed_loop_control_period`, `with_closed_loop_max_voltage`,
  `with_closed_loop_tolerance`, `with_closed_loop_ramp_rate`,
  `with_open_loop_ramp_rate`, `with_continuous_wrapping`,
  `with_measurement_limits`, `with_mechanism_limits`,
  `with_lqr`, `with_linear_closed_loop_controller`.
- Feedforward and profiles: `with_feedforward`, `with_trapezoid_profile`,
  `with_linear_trapezoid_profile`, `with_exponential_profile`,
  `with_linear_exponential_profile`, `with_velocity_trapezoid_profile`.
- Starting state: `with_starting_position`,
  `with_sim_starting_position`. Both are overloaded for degrees and meters;
  because units are represented as `float`, the degree overload is selected
  when a plain number is passed.
- Simulation: `with_sim_motor`, `with_sim_feedforward`,
  `with_sim_closed_loop_controller`,
  `with_simulation_period`, `with_sim_trapezoid_profile`,
  `with_sim_exponential_profile`.
- Limits and electrical: `with_stator_current_limit`,
  `with_supply_current_limit`, `with_temperature_cutoff`,
  `with_voltage_compensation`, `with_zero_power`.
- Robot integration: `with_subsystem`, `with_telemetry`, `with_followers`,
  `with_loosely_coupled_followers`, `clear_followers`.
- Getters include `get_kp`, `get_ki`, `get_kd`, `get_slot_gains`,
  `get_motor_gearing`, `get_motor_inverted`, `get_encoder_inverted`,
  `get_subsystem`, `has_subsystem`, and the corresponding `get_*` for the
  builders above.

Enum values:

- `MotorMode.coast`, `MotorMode.brake`
- `ControlMode.closed_loop`, `ControlMode.open_loop`
- `TelemetryVerbosity.none`, `.low`, `.medium`, `.high`
- `ClosedLoopControllerSlot.slot_0` ... `.slot_3`

Note: in simulation, upstream `GetMotorInverted()` returns `False`; use the
configuration you supplied rather than this getter to reason about inversion.

## Mechanisms

`Arm`, `Elevator`, `Pivot` and `FlyWheel` derive from `SmartMechanism`; the
positional mechanisms derive from `SmartPositionalMechanism` and the flywheel
derives from `SmartVelocityMechanism`.

```python
Arm(config: ArmConfig, smc: SmartMotorController)
Elevator(config: ElevatorConfig, smc: SmartMotorController)
Pivot(config: PivotConfig, smc: SmartMotorController)
FlyWheel(config: FlyWheelConfig, smc: SmartMotorController)
```

Common methods:

- State: `get_name`, `get_motor_controller`, `get_measurement_setpoint`,
  `get_mechanism_setpoint`, `get_mechanism_window`, `get_pose3d`.
- Control: `set_duty_cycle_setpoint`, `set_voltage_setpoint`,
  `set_mechanism_position_setpoint`, `set_mechanism_velocity_setpoint`,
  `set_measurement_position_setpoint`, `set_measurement_velocity_setpoint`,
  `run`, `run_to`, `set`.
- Simulation: `sim_iterate()` advances the mechanism and its motor controller.
- Telemetry/visualisation: `update_telemetry`, `visualization_update`.

Positional mechanisms add `get_angle`/`set_angle` (Arm, Pivot) or
`get_height`/`set_height` (Elevator), `is_near`, `min`, `max`, `between`,
`gte`, `lte`, and `get_mechanism_ligament`/`get_mechanism_root` for
visualisation. `FlyWheel` adds `get_velocity`, `set_velocity`,
`set_surface_speed`.

Important: calling `smc.sim_iterate()` alone does not advance a mechanism. Call
`mechanism.sim_iterate()` so that the mechanism feeds the simulated plant.

## `SimMotorController`

A simulated `SmartMotorController` that implements the full controller
interface without hardware:

```python
SimMotorController(config: SmartMotorControllerConfig)
```

Methods include `get_config`, `apply_config`, `get_duty_cycle`,
`set_duty_cycle`, `get_voltage`, `set_voltage`, `get_rotor_position`,
`set_encoder_position`, `get_rotor_velocity`, `set_encoder_velocity`,
`get_mechanism_position`, `get_mechanism_velocity`,
`get_measurement_position`, `get_measurement_velocity`,
`get_supply_current`, `get_stator_current`, `get_temperature`,
`iterate_closed_loop_controller`, `sim_iterate`, and `close`.

The adapter is defined in `cpp/include/yams/python/SimMotorController.hpp` and
`cpp/src/SimMotorController.cpp`.

## `SimSubsystem` and `SubsystemBase`

`SimSubsystem` is a concrete `wpi::cmd::SubsystemBase` for Python code:

```python
SimSubsystem(name: str = ...)
```

Methods: `get_name()`, `set_name(name)`.

`SmartMotorControllerConfig.with_subsystem()` requires a subsystem. Construct
`SimSubsystem` for simulation/testing, or subclass `SubsystemBase` in Python
(its constructor is bound) when integrating with additional command code.

## Simulation suppliers

`SimSupplier` is the abstract simulation interface. Concrete implementations:
`DCMotorSimSupplier`, `ArmSimSupplier`, `ElevatorSimSupplier`. They provide
`get_rotor_position`, `set_rotor_position`, `get_rotor_velocity`,
`set_rotor_velocity`, `get_mechanism_position`, `set_mechanism_position`,
`get_mechanism_velocity`, `set_mechanism_velocity`,
`set_mechanism_stator_voltage`, `set_mechanism_stator_duty_cycle`,
`feed_input`, `feed_update_sim`, `update_sim`, `starve_input`,
`starve_update_sim`, `is_input_fed`, `get_updated_sim`, `get_supply_current`,
`get_stator_current`, and related acceleration/voltage getters.

## Telemetry

`SmartMotorControllerTelemetry`, `MechanismTelemetry`,
`UnsupportedTelemetryFields`, `BooleanTelemetryField`, and
`DoubleTelemetryField` are exported. The upstream
`SmartMotorControllerTelemetryConfig` is intentionally not bound: it is
non-copyable and libstdc++ incorrectly reports it as copy-constructible, which
prevents safe ownership handling. Configure telemetry through
`SmartMotorControllerConfig.with_telemetry(...)` instead.

## Exceptions

All exceptions derive from `yams.YamsException`, which derives from Python's
`Exception`:

- `YamsException`
- `ArmConfigurationException`
- `ElevatorConfigurationException`
- `PivotConfigurationException`
- `SmartMotorControllerConfigurationException`
- `SwerveDriveConfigurationException`
- `NoStagesGivenException`
- `InvalidStageGivenException`

They are registered with `py::register_exception`, not bound as ordinary
classes, so `except yams.SmartMotorControllerConfigurationException:` works as
expected.

## Other functions

`to_robot_attitude(axis: GyroAxis, gyro_attitude) -> ...` rotates a gyro's
attitude into the robot frame. The `gyro_attitude` argument is a WPILib
`Rotation3d`, which is not bound by this project; the function is therefore
only usable if such a value is obtained from another extension.
