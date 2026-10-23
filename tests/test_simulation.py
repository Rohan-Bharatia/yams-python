"""Tests for the simulated motor controller and mechanism integration."""

import math

import pytest

import yams


def make_config(name="arm", gearing=10.0, starting_angle=0.0):
    return (
        yams.SmartMotorControllerConfig()
        .with_motor_gearing(gearing)
        .with_subsystem(yams.SimSubsystem(name))
        .with_starting_position(starting_angle)
    )


def make_arm(**kwargs):
    config = make_config(**kwargs)
    smc = yams.SimMotorController(config)
    arm = (
        yams.ArmConfig()
        .with_arm_length(1.0)
        .with_min_angle(-90.0)
        .with_max_angle(90.0)
    )
    return config, smc, yams.Arm(arm, smc)


def test_sim_subsystem_name():
    subsystem = yams.SimSubsystem("elevator")
    assert subsystem.get_name() == "elevator"


def test_sim_motor_controller_construction():
    config, smc, arm = make_arm()
    assert smc.get_config() is config
    assert arm.get_angle() == pytest.approx(0.0)
    assert smc.get_mechanism_position() == pytest.approx(0.0)


def test_starting_position_is_applied():
    config, smc, arm = make_arm(starting_angle=15.0)
    assert arm.get_angle() == pytest.approx(15.0)


def test_open_loop_moves_mechanism():
    config, smc, arm = make_arm()
    smc.set_duty_cycle(0.5)
    for _ in range(5):
        arm.sim_iterate()
    assert math.isfinite(arm.get_angle())
    assert arm.get_angle() != pytest.approx(0.0)


def test_voltage_roundtrip():
    config, smc, arm = make_arm()
    smc.set_voltage(3.5)
    assert smc.get_voltage() == pytest.approx(3.5)
    smc.set_voltage(0.0)
    assert smc.get_voltage() == pytest.approx(0.0)


def test_encoder_set_and_read():
    config, smc, arm = make_arm(gearing=1.0)
    smc.set_encoder_position(0.25)
    assert smc.get_rotor_position() == pytest.approx(0.25)
    smc.set_encoder_velocity(1.0)
    assert smc.get_rotor_velocity() == pytest.approx(1.0)


def test_mechanism_limits_clamp_position():
    config, smc, arm = make_arm()
    smc.set_duty_cycle(1.0)
    for _ in range(200):
        arm.sim_iterate()
    assert arm.get_angle() <= 90.0 + 1e-6
