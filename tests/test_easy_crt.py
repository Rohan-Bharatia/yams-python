"""Tests for the EasyCRT absolute encoder solver."""

import pytest

import yams


def test_unique_range():
    solver = yams.EasyCRT(100, 20, 20)
    assert solver.get_unique_range() == pytest.approx(0.2)


def test_solve_at_zero():
    solver = yams.EasyCRT(100, 20, 20)
    assert solver.solve(0.0, 0.0) == pytest.approx(0.0)


def test_solve_stays_within_range():
    solver = yams.EasyCRT(100, 20, 20)
    angle = solver.solve(0.3, 0.3)
    assert angle is not None
    assert abs(angle) <= solver.get_unique_range() / 2 + 1e-9
