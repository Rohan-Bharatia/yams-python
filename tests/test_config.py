"""Tests for configuration builders and validation."""

import pytest

import yams


def test_smc_config_builder_roundtrip():
    config = (
        yams.SmartMotorControllerConfig()
        .with_motor_gearing(10.0)
        .with_encoder_inverted(True)
        .with_motor_inverted(True)
        .with_feedback(1.5, 0.0, 0.1)
    )
    assert config.get_motor_gearing().get_mechanism_to_rotor_ratio() == pytest.approx(10.0)
    assert config.get_encoder_inverted() is True
    assert config.get_kp() == pytest.approx(1.5)
    assert config.get_kd() == pytest.approx(0.1)


def test_arm_config_builder_roundtrip():
    config = (
        yams.ArmConfig()
        .with_arm_length(0.75)
        .with_min_angle(-45.0)
        .with_max_angle(45.0)
        .with_telemetry_name("MyArm")
    )
    assert config.get_arm_length() == pytest.approx(0.75)
    assert config.get_min_angle() == pytest.approx(-45.0)
    assert config.get_max_angle() == pytest.approx(45.0)
    assert config.get_telemetry_name() == "MyArm"


def test_elevator_config_builder_roundtrip():
    config = (
        yams.ElevatorConfig()
        .with_carriage_mass(2.5)
        .with_minimum_height(0.0)
        .with_maximum_height(1.5)
    )
    assert config.get_carriage_mass() == pytest.approx(2.5)
    assert config.get_min_height() == pytest.approx(0.0)
    assert config.get_max_height() == pytest.approx(1.5)


def test_flywheel_config_builder_roundtrip():
    config = yams.FlyWheelConfig().with_telemetry_name("Shooter")
    assert config.get_telemetry_name() == "Shooter"


def test_missing_subsystem_raises():
    config = yams.SmartMotorControllerConfig().with_motor_gearing(10.0)
    smc = yams.SimMotorController(config)
    with pytest.raises(yams.SmartMotorControllerConfigurationException):
        yams.Arm(yams.ArmConfig(), smc)
