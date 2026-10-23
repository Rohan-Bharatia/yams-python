// Copyright (c) 2026 YAMS Python contributors
// SPDX-License-Identifier: LGPL-3.0-or-later

#include "yams/python/SimMotorController.hpp"

#include <algorithm>
#include <cmath>

#include <wpi/framework/RobotBase.hpp>
#include <wpi/math/system/Models.hpp>

#include "yams/gearing/MechanismGearing.hpp"

namespace yams::python {

using namespace yams::motorcontrollers;
using namespace yams::gearing;

namespace {
// Nominal temperature reported by the simulated motor; no thermal model is simulated.
constexpr wpi::units::celsius_t kSimTemperature{20.0};
}  // namespace

SimMotorController::SimMotorController(SmartMotorControllerConfig* config)
    : m_smcConfig(config) {
  m_config = config;
  if (config) {
    if (auto simMotor = config->GetSimMotor()) m_dcMotor = *simMotor;
  }
}

SimMotorController::~SimMotorController() = default;

// ---- Configuration ----------------------------------------------------------

bool SimMotorController::ApplyConfig(const SmartMotorControllerConfig& config) {
  // The applied config becomes this controller's config.
  m_config = const_cast<SmartMotorControllerConfig*>(&config);
  m_smcConfig = m_config;
  config.ResetValidationCheck();

  // Closed loop gains from the active slot.
  const auto gains = config.GetSlotGains(m_slot);
  if (gains.lqr) {
    m_lqr = math::LQRController{*gains.lqr};
  } else {
    m_lqr.reset();
  }
  if (gains.kP != 0.0 || gains.kI != 0.0 || gains.kD != 0.0) {
    m_pid = wpi::math::PIDController{gains.kP, gains.kI, gains.kD,
                                     config.GetClosedLoopControlPeriod().value_or(20_ms)};
  } else {
    m_pid.reset();
  }
  ConfigureSoftwarePID(config);

  if (auto inverted = config.GetMotorInverted()) m_motorInverted = *inverted;
  if (auto inverted = config.GetEncoderInverted()) m_encoderInverted = *inverted;
  if (auto lower = config.GetMechanismLowerLimit()) m_lowerLimit = *lower;
  if (auto upper = config.GetMechanismUpperLimit()) m_upperLimit = *upper;
  m_measurementLowerLimit = config.GetMeasurementLowerLimit();
  m_measurementUpperLimit = config.GetMeasurementUpperLimit();
  if (auto simMotor = config.GetSimMotor()) m_dcMotor = *simMotor;

  LoadLooselyCoupledFollowers();

  config.ValidateBasicOptions();
  config.ValidateExternalEncoderOptions();
  return true;
}

// ---- Simulation -------------------------------------------------------------

void SimMotorController::SetupSimulation() {
  if (!wpi::RobotBase::IsSimulation()) return;
  // A mechanism may have installed its own supplier (e.g. an Arm installs an ArmSimSupplier).
  if (m_simSupplier) return;
  if (!m_smcConfig) return;

  const auto simMotor = m_smcConfig->GetSimMotor().value_or(m_dcMotor);
  const double mechanismToRotor = MechanismToRotorRatio();
  const auto plant = wpi::math::Models::SingleJointedArmFromPhysicalConstants(
      simMotor, m_smcConfig->GetMOI(), mechanismToRotor);
  m_motorSim.emplace(plant, simMotor);

  m_dcmotorSimSupplier =
      std::make_shared<simulation::DCMotorSimSupplier>(*m_motorSim, *this);
  m_simSupplier = m_dcmotorSimSupplier;

  if (auto start = m_smcConfig->GetStartingPosition()) {
    m_simSupplier->SetMechanismPosition(*start);
    m_rotorPosition = *start * MechanismToRotorRatio();
  }
}

void SimMotorController::SimIterate() {
  // The closed loop output is computed here so that it is applied to the plant on the next
  // simulation step (the mechanism calls UpdateSim() before SimIterate()).
  if (m_setpointPosition || m_setpointVelocity) {
    const double output = ComputeClosedLoopOutput();
    SetVoltage(wpi::units::volt_t{output});
  }

  if (!m_simSupplier) {
    // Stand-alone use: integrate the commanded duty cycle.
    const wpi::units::second_t dt =
        m_smcConfig ? m_smcConfig->GetSimulationPeriod() : wpi::units::second_t{0.020};
    const double maxVelocity = m_dcMotor.freeSpeed.value();
    m_rotorVelocity = wpi::units::turns_per_second_t{
        std::clamp(m_rotorVelocity.value() + m_dutyCycle * maxVelocity * dt.value(),
                   -maxVelocity, maxVelocity)};
    m_rotorPosition = m_rotorPosition + m_rotorVelocity * dt;
  }
}

// ---- Encoder sync -----------------------------------------------------------

void SimMotorController::SeedRelativeEncoder() {
  // The simulated encoder is absolute; the relative encoder mirrors it.
}

void SimMotorController::SynchronizeRelativeEncoder() {
  // The simulated encoder is absolute; the relative encoder mirrors it.
}

// ---- Open loop outputs ------------------------------------------------------

void SimMotorController::SetDutyCycle(double dutyCycle) {
  m_dutyCycle = std::clamp(dutyCycle, -1.0, 1.0);
  m_voltage = wpi::units::volt_t{m_dutyCycle * SupplyVoltage().value()};
  if (m_dutyCycle == 0.0) {
    for (auto* f : m_looseFollowers) f->SetDutyCycle(0.0);
  }
}

double SimMotorController::GetDutyCycle() { return m_dutyCycle; }

void SimMotorController::SetVoltage(wpi::units::volt_t voltage) {
  m_voltage = voltage;
  const double supply = SupplyVoltage().value();
  m_dutyCycle = supply != 0.0 ? std::clamp(voltage.value() / supply, -1.0, 1.0) : 0.0;
}

wpi::units::volt_t SimMotorController::GetVoltage() { return m_voltage; }

// ---- Closed loop setpoints --------------------------------------------------

void SimMotorController::SetPosition(wpi::units::turn_t angle) {
  m_setpointVelocity.reset();
  m_setpointFeedforwardForce.reset();
  m_setpointPosition = angle;
  ForwardPositionToFollowers(angle);
}

void SimMotorController::SetPosition(wpi::units::meter_t distance) {
  SetPosition(m_config->ConvertToMechanism(distance));
}

void SimMotorController::SetVelocity(wpi::units::turns_per_second_t velocity) {
  m_setpointPosition.reset();
  m_setpointFeedforwardForce.reset();
  m_setpointVelocity = velocity;
  ForwardVelocityToFollowers(velocity);
}

void SimMotorController::SetVelocity(wpi::units::meters_per_second_t velocity) {
  SetVelocity(m_config->ConvertToMechanism(velocity));
}

// ---- Encoder writes ---------------------------------------------------------

void SimMotorController::SetEncoderPosition(wpi::units::turn_t angle) {
  m_rotorPosition = angle * MechanismToRotorRatio();
  if (m_simSupplier) m_simSupplier->SetMechanismPosition(angle);
}

void SimMotorController::SetEncoderPosition(wpi::units::meter_t distance) {
  SetEncoderPosition(m_config->ConvertToMechanism(distance));
}

void SimMotorController::SetEncoderVelocity(wpi::units::turns_per_second_t velocity) {
  m_rotorVelocity = velocity * MechanismToRotorRatio();
  if (m_simSupplier) m_simSupplier->SetMechanismVelocity(velocity);
}

void SimMotorController::SetEncoderVelocity(wpi::units::meters_per_second_t velocity) {
  SetEncoderVelocity(m_config->ConvertToMechanism(velocity));
}

// ---- Encoder reads ----------------------------------------------------------

wpi::units::turn_t SimMotorController::GetMechanismPosition() {
  if (m_simSupplier) return m_simSupplier->GetMechanismPosition();
  return m_rotorPosition * RotorToMechanismRatio();
}

wpi::units::turns_per_second_t SimMotorController::GetMechanismVelocity() {
  if (m_simSupplier) return m_simSupplier->GetMechanismVelocity();
  return m_rotorVelocity * RotorToMechanismRatio();
}

wpi::units::turn_t SimMotorController::GetRelativeMechanismPosition() {
  return GetMechanismPosition();
}

wpi::units::turns_per_second_t SimMotorController::GetRelativeMechanismVelocity() {
  return GetMechanismVelocity();
}

wpi::units::turns_per_second_squared_t SimMotorController::GetMechanismAcceleration() {
  if (m_simSupplier) return m_simSupplier->GetMechanismAcceleration();
  return wpi::units::turns_per_second_squared_t{0.0};
}

wpi::units::turn_t SimMotorController::GetRotorPosition() {
  if (m_simSupplier) return m_simSupplier->GetRotorPosition();
  return m_rotorPosition;
}

wpi::units::turns_per_second_t SimMotorController::GetRotorVelocity() {
  if (m_simSupplier) return m_simSupplier->GetRotorVelocity();
  return m_rotorVelocity;
}

wpi::units::meter_t SimMotorController::GetMeasurementPosition() {
  if (!m_config || !m_config->GetMechanismCircumference()) return wpi::units::meter_t{0.0};
  return m_config->ConvertFromMechanism(GetMechanismPosition());
}

wpi::units::meters_per_second_t SimMotorController::GetMeasurementVelocity() {
  if (!m_config || !m_config->GetMechanismCircumference()) return wpi::units::meters_per_second_t{0.0};
  return m_config->ConvertFromMechanism(GetMechanismVelocity());
}

wpi::units::meters_per_second_squared_t SimMotorController::GetMeasurementAcceleration() {
  if (!m_config || !m_config->GetMechanismCircumference()) {
    return wpi::units::meters_per_second_squared_t{0.0};
  }
  return m_config->ConvertFromMechanism(GetMechanismAcceleration());
}

std::optional<wpi::units::turn_t> SimMotorController::GetExternalEncoderMechanismPosition() {
  return std::nullopt;
}

std::optional<wpi::units::turns_per_second_t>
SimMotorController::GetExternalEncoderMechanismVelocity() {
  return std::nullopt;
}

// ---- Motor status -----------------------------------------------------------

std::optional<wpi::units::ampere_t> SimMotorController::GetSupplyCurrent() {
  if (m_simSupplier) return m_simSupplier->GetSupplyCurrent();
  return std::nullopt;
}

wpi::units::ampere_t SimMotorController::GetStatorCurrent() {
  if (m_simSupplier) return m_simSupplier->GetStatorCurrent();
  return wpi::units::ampere_t{0.0};
}

wpi::units::celsius_t SimMotorController::GetTemperature() { return kSimTemperature; }

wpi::math::DCMotor SimMotorController::GetDCMotor() { return m_dcMotor; }

// ---- Configuration setters --------------------------------------------------

void SimMotorController::SetZeroPower(MotorMode mode) {
  m_config->WithZeroPower(mode);
}

void SimMotorController::SetMotorInverted(bool inverted) {
  m_motorInverted = inverted;
  m_config->WithMotorInverted(inverted);
}

void SimMotorController::SetEncoderInverted(bool inverted) {
  m_encoderInverted = inverted;
  m_config->WithEncoderInverted(inverted);
}

void SimMotorController::SetKp(double kP) {
  if (m_pid) {
    m_pid->SetP(kP);
  }
}

void SimMotorController::SetKi(double kI) {
  if (m_pid) {
    m_pid->SetI(kI);
  }
}

void SimMotorController::SetKd(double kD) {
  if (m_pid) {
    m_pid->SetD(kD);
  }
}

void SimMotorController::SetFeedback(double kP, double kI, double kD) {
  if (m_pid) {
    m_pid->SetPID(kP, kI, kD);
  }
}

void SimMotorController::SetKs(double kS) {}
void SimMotorController::SetKv(double kV) {}
void SimMotorController::SetKa(double kA) {}
void SimMotorController::SetKg(double kG) {}

void SimMotorController::SetFeedforward(double kS, double kV, double kA, double kG) {}

void SimMotorController::SetStatorCurrentLimit(wpi::units::ampere_t currentLimit) {
  m_config->WithStatorCurrentLimit(currentLimit);
}

void SimMotorController::SetSupplyCurrentLimit(wpi::units::ampere_t currentLimit) {
  m_config->WithSupplyCurrentLimit(currentLimit);
}

void SimMotorController::SetClosedLoopRampRate(wpi::units::second_t rampRate) {
  m_config->WithClosedLoopRampRate(rampRate);
}

void SimMotorController::SetOpenLoopRampRate(wpi::units::second_t rampRate) {
  m_config->WithOpenLoopRampRate(rampRate);
}

void SimMotorController::SetMechanismUpperLimit(wpi::units::turn_t upperLimit) {
  m_upperLimit = upperLimit;
  m_config->WithMechanismLimits(m_lowerLimit, upperLimit);
}

void SimMotorController::SetMechanismLowerLimit(wpi::units::turn_t lowerLimit) {
  m_lowerLimit = lowerLimit;
  m_config->WithMechanismLimits(lowerLimit, m_upperLimit);
}

void SimMotorController::SetMechanismLimits(wpi::units::turn_t lower, wpi::units::turn_t upper) {
  m_lowerLimit = lower;
  m_upperLimit = upper;
  m_config->WithMechanismLimits(lower, upper);
}

void SimMotorController::SetMechanismLimitsEnabled(bool enabled) { m_limitsEnabled = enabled; }

void SimMotorController::SetMeasurementUpperLimit(wpi::units::meter_t upperLimit) {
  m_measurementUpperLimit = upperLimit;
  if (m_measurementLowerLimit) {
    m_config->WithMeasurementLimits(*m_measurementLowerLimit, upperLimit);
  }
}

void SimMotorController::SetMeasurementLowerLimit(wpi::units::meter_t lowerLimit) {
  m_measurementLowerLimit = lowerLimit;
  if (m_measurementUpperLimit) {
    m_config->WithMeasurementLimits(lowerLimit, *m_measurementUpperLimit);
  }
}

void SimMotorController::SetMotionProfileMaxVelocity(wpi::units::turns_per_second_t maxVelocity) {
  m_profileMaxVelocity = maxVelocity;
  if (m_profileMaxAcceleration) {
    m_config->WithTrapezoidProfile(*m_profileMaxVelocity, *m_profileMaxAcceleration);
  }
}

void SimMotorController::SetMotionProfileMaxVelocity(wpi::units::meters_per_second_t maxVelocity) {
  m_linearProfileMaxVelocity = maxVelocity;
  if (m_linearProfileMaxAcceleration) {
    m_config->WithLinearTrapezoidProfile(*m_linearProfileMaxVelocity, *m_linearProfileMaxAcceleration);
  }
}

void SimMotorController::SetMotionProfileMaxAcceleration(
    wpi::units::turns_per_second_squared_t maxAcc) {
  m_profileMaxAcceleration = maxAcc;
  if (m_profileMaxVelocity) {
    m_config->WithTrapezoidProfile(*m_profileMaxVelocity, *m_profileMaxAcceleration);
  }
}

void SimMotorController::SetMotionProfileMaxAcceleration(
    wpi::units::meters_per_second_squared_t maxAcc) {
  m_linearProfileMaxAcceleration = maxAcc;
  if (m_linearProfileMaxVelocity) {
    m_config->WithLinearTrapezoidProfile(*m_linearProfileMaxVelocity,
                                         *m_linearProfileMaxAcceleration);
  }
}

void SimMotorController::SetMotionProfileMaxJerk(
    wpi::units::angular_jerk::turns_per_second_cubed_t maxJerk) {}

void SimMotorController::SetExponentialProfile(std::optional<double> kV, std::optional<double> kA,
                                               std::optional<wpi::units::volt_t> maxInput) {
  if (kV && kA) {
    m_config->WithExponentialProfile(*kV, *kA, maxInput.value_or(12_V));
  }
}

void SimMotorController::SetClosedLoopSlot(ClosedLoopControllerSlot slot) {
  m_slot = slot;
  if (!m_smcConfig) return;
  const auto gains = m_smcConfig->GetSlotGains(slot);
  if (gains.kP != 0.0 || gains.kI != 0.0 || gains.kD != 0.0) {
    m_pid = wpi::math::PIDController{gains.kP, gains.kI, gains.kD,
                                     m_smcConfig->GetClosedLoopControlPeriod().value_or(20_ms)};
  } else {
    m_pid.reset();
  }
  ConfigureSoftwarePID(*m_smcConfig);
}

motorcontrollers::SmartMotorControllerConfig& SimMotorController::GetConfig() { return *m_config; }

void* SimMotorController::GetMotorController() { return this; }

void* SimMotorController::GetMotorControllerConfig() { return m_config; }

// ---- Helpers ----------------------------------------------------------------

double SimMotorController::ComputeClosedLoopOutput() {
  double output = 0.0;

  if (m_setpointPosition) {
    const double measured = GetMechanismPosition().value();
    const double setpoint = m_setpointPosition->value();
    if (m_pid) {
      output += m_pid->Calculate(measured, setpoint);
    }
  } else if (m_setpointVelocity) {
    const double measured = GetMechanismVelocity().value();
    const double setpoint = m_setpointVelocity->value();
    if (m_pid) {
      output += m_pid->Calculate(measured, setpoint);
    }
  }

  // Feedforward: static and velocity gains.
  const auto gains = m_smcConfig ? m_smcConfig->GetSlotGains(m_slot)
                                 : SmartMotorControllerConfig::PIDGains{};
  if (m_setpointPosition || m_setpointVelocity) {
    const double velocitySetpoint =
        m_setpointVelocity ? m_setpointVelocity->value() : GetMechanismVelocity().value();
    output += gains.kS * std::copysign(1.0, output != 0.0 ? output : velocitySetpoint);
    output += gains.kV * velocitySetpoint;
  }

  // Soft limits.
  if (m_limitsEnabled) {
    const auto position = GetMechanismPosition();
    if (position > m_upperLimit && output > 0.0) output = 0.0;
    if (position < m_lowerLimit && output < 0.0) output = 0.0;
  }

  // Maximum voltage.
  if (m_smcConfig) {
    if (auto maxVoltage = m_smcConfig->GetClosedLoopControllerMaximumVoltage()) {
      output = std::clamp(output, -maxVoltage->value(), maxVoltage->value());
    }
  }

  return output;
}

wpi::units::volt_t SimMotorController::SupplyVoltage() const {
  if (m_simSupplier) return m_simSupplier->GetMechanismSupplyVoltage();
  return m_dcMotor.nominalVoltage;
}

double SimMotorController::RotorToMechanismRatio() const {
  if (!m_smcConfig) return 1.0;
  return m_smcConfig->GetMotorGearing().value_or(MechanismGearing::kOne).GetRotorToMechanismRatio();
}

double SimMotorController::MechanismToRotorRatio() const {
  if (!m_smcConfig) return 1.0;
  return m_smcConfig->GetMotorGearing().value_or(MechanismGearing::kOne).GetMechanismToRotorRatio();
}

}  // namespace yams::python
