"""Tests for GearBox, Sprocket and MechanismGearing."""

import pytest

import yams


def test_gearbox_vector_constructor():
    gearbox = yams.GearBox([10.0, 2.0])
    assert gearbox.get_input_to_output_conversion_factor() == pytest.approx(0.05)
    assert gearbox.get_output_to_input_conversion_factor() == pytest.approx(20.0)


def test_gearbox_from_reduction_stages():
    gearbox = yams.GearBox.from_reduction_stages([10.0, 2.0])
    assert gearbox.get_input_to_output_conversion_factor() == pytest.approx(0.05)


def test_gearbox_from_stages():
    gearbox = yams.GearBox.from_stages(["10:1", "2:1"])
    assert gearbox.get_input_to_output_conversion_factor() == pytest.approx(0.05)


def test_gearbox_from_teeth():
    gearbox = yams.GearBox.from_teeth([12, 36, 12, 36])
    assert gearbox.get_input_to_output_conversion_factor() == pytest.approx(1.0 / 3.0)


def test_gearbox_from_teeth_rejects_single_gear():
    with pytest.raises(ValueError):
        yams.GearBox.from_teeth([12])


def test_gearbox_from_teeth_rejects_non_positive():
    with pytest.raises(ValueError):
        yams.GearBox.from_teeth([12, 0])


def test_gearbox_times_and_div():
    gearbox = yams.GearBox(4.0).times(2.0).div(4.0)
    assert gearbox.get_input_to_output_conversion_factor() == pytest.approx(0.125)
    assert gearbox.get_output_to_input_conversion_factor() == pytest.approx(8.0)


def test_sprocket_from_stages():
    sprocket = yams.Sprocket.from_stages(["10:1", "2:1"])
    assert sprocket.get_input_to_output_conversion_factor() == pytest.approx(20.0)


def test_mechanism_gearing():
    gearing = yams.MechanismGearing(yams.GearBox(10.0))
    assert gearing.get_rotor_to_mechanism_ratio() == pytest.approx(0.1)
    assert gearing.get_mechanism_to_rotor_ratio() == pytest.approx(10.0)


def test_mechanism_gearing_with_sprocket():
    gearing = yams.MechanismGearing(yams.GearBox(10.0), yams.Sprocket(2.0))
    assert gearing.get_rotor_to_mechanism_ratio() == pytest.approx(0.2)
    assert gearing.get_mechanism_to_rotor_ratio() == pytest.approx(5.0)
