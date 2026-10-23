// Copyright (c) 2026 YAMS Python contributors
// SPDX-License-Identifier: LGPL-3.0-or-later
//
// pybind11 type casters for the WPILib unit types.
//
// WPILib's unit types (``wpi::units::turn_t``, ``wpi::units::meter_t``, ...) are
// thin wrappers around a double.  They are exposed to Python as plain floats
// holding the value in the unit's own scale (turns, meters, volts, ...), which
// is the same convention RobotPy uses.

#pragma once

#include <pybind11/pybind11.h>

#include <wpi/units/base.hpp>

namespace pybind11::detail {

template <typename Units, typename T, template <typename> class NonLinearScale>
struct type_caster<wpi::units::unit_t<Units, T, NonLinearScale>> {
  using Unit = wpi::units::unit_t<Units, T, NonLinearScale>;

  PYBIND11_TYPE_CASTER(Unit, _("float"));

  bool load(handle src, bool /*convert*/) {
    if (!src) {
      return false;
    }
    if (!PyNumber_Check(src.ptr())) {
      return false;
    }
    try {
      value = Unit{static_cast<T>(src.cast<double>())};
    } catch (const std::exception&) {
      return false;
    }
    return true;
  }

  static handle cast(const Unit& src, return_value_policy /*policy*/, handle /*parent*/) {
    return PyFloat_FromDouble(static_cast<double>(src.value()));
  }
};

}  // namespace pybind11::detail
