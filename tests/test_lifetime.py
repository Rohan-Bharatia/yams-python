"""Lifetime and ownership safety tests."""

import gc

import yams


def test_get_config_keeps_objects_valid():
    config = (
        yams.SmartMotorControllerConfig()
        .with_motor_gearing(5.0)
        .with_subsystem(yams.SimSubsystem("test"))
    )
    smc = yams.SimMotorController(config)
    c = smc.get_config()
    del config
    gc.collect()
    assert c.get_motor_gearing().get_mechanism_to_rotor_ratio() == 5.0
