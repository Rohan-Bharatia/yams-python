"""Tests for the math helpers."""

import pytest

import yams


def test_gear_box_ratio():
    assert yams.SmartMath.gear_box([10.0, 2.0]) == pytest.approx(20.0)


def test_sensor_to_mechanism_ratio():
    assert yams.SmartMath.sensor_to_mechanism_ratio([3.0, 4.0]) == pytest.approx(12.0)


def test_empty_stages_raise():
    with pytest.raises(yams.NoStagesGivenException):
        yams.SmartMath.gear_box([])
    with pytest.raises(yams.NoStagesGivenException):
        yams.SmartMath.sensor_to_mechanism_ratio([])


def test_lqr_config_builder():
    config = (
        yams.LQRConfig()
        .with_q_elems([1.0, 2.0])
        .with_r_elems([12.0])
        .with_state_std_devs([0.1, 0.1])
        .with_measurement_std_devs([0.01])
    )
    assert config.get_period() == pytest.approx(0.020)
    assert config.get_max_voltage() == pytest.approx(12.0)


def test_derivative_time_filter():
    filt = yams.DerivativeTimeFilter(1.0, 0.1)
    assert filt.derivative(1.0) == pytest.approx(0.0)
