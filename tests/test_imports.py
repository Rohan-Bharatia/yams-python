"""Smoke tests that the extension module exposes the expected API."""

import yams


def test_public_classes():
    expected = [
        "Arm",
        "ArmConfig",
        "Elevator",
        "ElevatorConfig",
        "FlyWheel",
        "FlyWheelConfig",
        "GearBox",
        "LQRConfig",
        "LQRController",
        "MechanismGearing",
        "Pivot",
        "PivotConfig",
        "SimMotorController",
        "SimSubsystem",
        "SmartMath",
        "SmartMechanism",
        "SmartMotorController",
        "SmartMotorControllerConfig",
        "Sprocket",
    ]
    for name in expected:
        assert hasattr(yams, name), name


def test_exceptions_are_exceptions():
    assert issubclass(yams.YamsException, Exception)
    assert issubclass(yams.SmartMotorControllerConfigurationException, yams.YamsException)
    assert issubclass(yams.ArmConfigurationException, yams.YamsException)


def test_enum_values():
    assert yams.SmartMotorControllerConfig.MotorMode.brake is not None
    assert yams.GyroAxis.yaw is not None
