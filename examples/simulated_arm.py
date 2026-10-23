"""Drive a simulated YAMS arm without any hardware.

After installing the wheel simply run::

    python examples/simulated_arm.py

When using an uninstalled development build, put the repository root on
``PYTHONPATH`` first::

    PYTHONPATH=. python examples/simulated_arm.py
"""

from __future__ import annotations

import yams


def main() -> None:
    motor_config = (
        yams.SmartMotorControllerConfig()
        .with_motor_gearing(10.0)
        .with_subsystem(yams.SimSubsystem("example_arm"))
        .with_starting_position(0.0)
    )
    motor = yams.SimMotorController(motor_config)

    arm_config = (
        yams.ArmConfig()
        .with_arm_length(1.0)
        .with_min_angle(-90.0)
        .with_max_angle(90.0)
    )
    arm = yams.Arm(arm_config, motor)

    print(f"initial angle: {arm.get_angle():.3f} deg")
    motor.set_duty_cycle(0.5)
    for _ in range(10):
        arm.sim_iterate()
    print(f"after 10 steps: {arm.get_angle():.3f} deg")


if __name__ == "__main__":
    main()
