// Copyright (c) 2026 YAMS Python contributors
// SPDX-License-Identifier: LGPL-3.0-or-later
//
// A minimal concrete ``wpi::cmd::SubsystemBase`` implementation.
//
// YAMS mechanisms require every ``SmartMotorControllerConfig`` to reference a
// command subsystem.  WPILib's ``SubsystemBase`` has protected constructors, so
// this trivial subclass makes it possible to create a subsystem from Python
// without pulling in the full command framework.

#pragma once

#include <string_view>

#include <wpi/commands2/SubsystemBase.hpp>

namespace yams::python {

class SimSubsystem : public wpi::cmd::SubsystemBase {
 public:
  SimSubsystem() = default;
  explicit SimSubsystem(std::string_view name) : wpi::cmd::SubsystemBase(name) {}
};

}  // namespace yams::python
