// Copyright (c) 2026 YAMS Python contributors
// SPDX-License-Identifier: LGPL-3.0-or-later
//
// A concrete, vendor independent ``SmartMotorController`` implementation that
// simulates a motor in software.
//
// YAMS ships vendor specific motor controller wrappers (CTRE TalonFX/TalonFXS,
// REV Spark Max, ThriftyLib Nova) that wrap real hardware.  Those wrappers
// cannot be used from Python because the vendor libraries are not
// redistributable, and the abstract ``SmartMotorController`` cannot be
// instantiated directly.  ``SimMotorController`` fills that gap: it implements
// the full YAMS motor controller interface on top of WPILib's ``DCMotorSim``,
// which is what the mechanism classes (Arm, Elevator, Pivot, FlyWheel) use to
// run in simulation.

#pragma once

#include <memory>
#include <optional>

#include <wpi/math/system/DCMotor.hpp>
#include <wpi/simulation/DCMotorSim.hpp>
#include <wpi/units/acceleration.hpp>
#include <wpi/units/angle.hpp>
#include <wpi/units/angular_acceleration.hpp>
#include <wpi/units/angular_velocity.hpp>
#include <wpi/units/current.hpp>
#include <wpi/units/length.hpp>
#include <wpi/units/temperature.hpp>
#include <wpi/units/time.hpp>
#include <wpi/units/velocity.hpp>
#include <wpi/units/voltage.hpp>

#include "yams/motorcontrollers/SmartMotorController.hpp"
#include "yams/motorcontrollers/SmartMotorControllerConfig.hpp"
#include "yams/motorcontrollers/simulation/DCMotorSimSupplier.hpp"

namespace yams::python {

/**
 * A simulated motor controller.
 *
 * The controller keeps track of the commanded duty cycle/voltage.  In simulation the rotor
 * state is driven by WPILib's ``DCMotorSim``; when no simulation supplier is installed (i.e. the
 * controller is used stand-alone) the rotor state is integrated from the commanded duty cycle.
 */
class SimMotorController : public motorcontrollers::SmartMotorController {
 public:
  /**
   * Create a simulated motor controller.
   *
   * @param config Configuration for the controller.  The configuration object must outlive the
   *               controller.
   */
  explicit SimMotorController(motorcontrollers::SmartMotorControllerConfig* config);

  ~SimMotorController() override;

  // ---- Configuration ------------------------------------------------------
  bool ApplyConfig(const motorcontrollers::SmartMotorControllerConfig& config) override;

  // ---- Simulation ---------------------------------------------------------
  void SetupSimulation() override;
  void SimIterate() override;

  // ---- Encoder sync -------------------------------------------------------
  void SeedRelativeEncoder() override;
  void SynchronizeRelativeEncoder() override;

  // ---- Open loop outputs --------------------------------------------------
  void SetDutyCycle(double dutyCycle) override;
  double GetDutyCycle() override;
  void SetVoltage(wpi::units::volt_t voltage) override;
  wpi::units::volt_t GetVoltage() override;

  // ---- Closed loop setpoints ----------------------------------------------
  void SetPosition(wpi::units::turn_t angle) override;
  void SetPosition(wpi::units::meter_t distance) override;
  void SetVelocity(wpi::units::turns_per_second_t velocity) override;
  void SetVelocity(wpi::units::meters_per_second_t velocity) override;

  // ---- Encoder writes -----------------------------------------------------
  void SetEncoderPosition(wpi::units::turn_t angle) override;
  void SetEncoderPosition(wpi::units::meter_t distance) override;
  void SetEncoderVelocity(wpi::units::turns_per_second_t velocity) override;
  void SetEncoderVelocity(wpi::units::meters_per_second_t velocity) override;

  // ---- Encoder reads ------------------------------------------------------
  wpi::units::turn_t GetMechanismPosition() override;
  wpi::units::turns_per_second_t GetMechanismVelocity() override;
  wpi::units::turn_t GetRelativeMechanismPosition() override;
  wpi::units::turns_per_second_t GetRelativeMechanismVelocity() override;
  wpi::units::turns_per_second_squared_t GetMechanismAcceleration() override;
  wpi::units::turn_t GetRotorPosition() override;
  wpi::units::turns_per_second_t GetRotorVelocity() override;
  wpi::units::meter_t GetMeasurementPosition() override;
  wpi::units::meters_per_second_t GetMeasurementVelocity() override;
  wpi::units::meters_per_second_squared_t GetMeasurementAcceleration() override;
  std::optional<wpi::units::turn_t> GetExternalEncoderMechanismPosition() override;
  std::optional<wpi::units::turns_per_second_t> GetExternalEncoderMechanismVelocity() override;

  // ---- Motor status -------------------------------------------------------
  std::optional<wpi::units::ampere_t> GetSupplyCurrent() override;
  wpi::units::ampere_t GetStatorCurrent() override;
  wpi::units::celsius_t GetTemperature() override;
  wpi::math::DCMotor GetDCMotor() override;

  // ---- Configuration setters ----------------------------------------------
  void SetZeroPower(MotorMode mode) override;
  void SetMotorInverted(bool inverted) override;
  void SetEncoderInverted(bool inverted) override;
  void SetKp(double kP) override;
  void SetKi(double kI) override;
  void SetKd(double kD) override;
  void SetFeedback(double kP, double kI, double kD) override;
  void SetKs(double kS) override;
  void SetKv(double kV) override;
  void SetKa(double kA) override;
  void SetKg(double kG) override;
  void SetFeedforward(double kS, double kV, double kA, double kG) override;
  void SetStatorCurrentLimit(wpi::units::ampere_t currentLimit) override;
  void SetSupplyCurrentLimit(wpi::units::ampere_t currentLimit) override;
  void SetClosedLoopRampRate(wpi::units::second_t rampRate) override;
  void SetOpenLoopRampRate(wpi::units::second_t rampRate) override;
  void SetMechanismUpperLimit(wpi::units::turn_t upperLimit) override;
  void SetMechanismLowerLimit(wpi::units::turn_t lowerLimit) override;
  void SetMechanismLimits(wpi::units::turn_t lower, wpi::units::turn_t upper) override;
  void SetMechanismLimitsEnabled(bool enabled) override;
  void SetMeasurementUpperLimit(wpi::units::meter_t upperLimit) override;
  void SetMeasurementLowerLimit(wpi::units::meter_t lowerLimit) override;
  void SetMotionProfileMaxVelocity(wpi::units::turns_per_second_t maxVelocity) override;
  void SetMotionProfileMaxVelocity(wpi::units::meters_per_second_t maxVelocity) override;
  void SetMotionProfileMaxAcceleration(wpi::units::turns_per_second_squared_t maxAcc) override;
  void SetMotionProfileMaxAcceleration(wpi::units::meters_per_second_squared_t maxAcc) override;
  void SetMotionProfileMaxJerk(
      wpi::units::angular_jerk::turns_per_second_cubed_t maxJerk) override;
  void SetExponentialProfile(std::optional<double> kV, std::optional<double> kA,
                             std::optional<wpi::units::volt_t> maxInput) override;
  void SetClosedLoopSlot(ClosedLoopControllerSlot slot) override;

  motorcontrollers::SmartMotorControllerConfig& GetConfig() override;
  void* GetMotorController() override;
  void* GetMotorControllerConfig() override;

 private:
  /** Compute the closed loop output (in volts) for the current setpoint. */
  double ComputeClosedLoopOutput();

  /** @return the supply voltage available to the motor. */
  wpi::units::volt_t SupplyVoltage() const;

  /** @return the rotor to mechanism ratio (OUT/IN). */
  double RotorToMechanismRatio() const;

  /** @return the mechanism to rotor ratio (IN/OUT). */
  double MechanismToRotorRatio() const;

  motorcontrollers::SmartMotorControllerConfig* m_smcConfig{nullptr};
  wpi::math::DCMotor m_dcMotor{wpi::math::DCMotor::NEO550()};
  std::optional<wpi::sim::DCMotorSim> m_motorSim;
  std::shared_ptr<motorcontrollers::simulation::DCMotorSimSupplier> m_dcmotorSimSupplier;

  double m_dutyCycle{0.0};
  wpi::units::volt_t m_voltage{0.0};

  wpi::units::turn_t m_rotorPosition{0.0};
  wpi::units::turns_per_second_t m_rotorVelocity{0.0};

  bool m_motorInverted{false};
  bool m_encoderInverted{false};
  bool m_limitsEnabled{true};
  wpi::units::turn_t m_upperLimit{0.0};
  wpi::units::turn_t m_lowerLimit{0.0};
  std::optional<wpi::units::meter_t> m_measurementUpperLimit;
  std::optional<wpi::units::meter_t> m_measurementLowerLimit;

  std::optional<wpi::units::turns_per_second_t> m_profileMaxVelocity;
  std::optional<wpi::units::turns_per_second_squared_t> m_profileMaxAcceleration;
  std::optional<wpi::units::meters_per_second_t> m_linearProfileMaxVelocity;
  std::optional<wpi::units::meters_per_second_squared_t> m_linearProfileMaxAcceleration;
};

}  // namespace yams::python
