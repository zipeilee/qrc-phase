"""Typed configuration and validation for the qrc-phase Python backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np

SUPPORTED_HAMILTONIAN_FAMILIES = {"essh"}
SUPPORTED_SOLVER_TYPES = {"vqe", "exact_state"}
SUPPORTED_EXACT_METHODS = {"auto", "dense_eigh", "sparse_eigsh"}
SUPPORTED_DTYPES = {"complex128", "complex64"}


class ConfigError(ValueError):
    """Raised when workflow configuration is invalid."""


@dataclass(slots=True)
class HamiltonianConfig:
    family: str = "essh"
    N: int = 0
    J1: float = 1.0
    J2: float = 0.5
    delta: float = 0.0
    periodic: bool = False
    penalty_z1: float = 0.01

    def validate(self) -> "HamiltonianConfig":
        family = self.family.lower()
        if family not in SUPPORTED_HAMILTONIAN_FAMILIES:
            raise ConfigError(f"Unsupported Hamiltonian family: {self.family}")
        if self.N <= 1:
            raise ConfigError("HamiltonianConfig.N must be greater than 1.")
        if self.periodic:
            raise ConfigError("Periodic boundary conditions are not supported in v1.")
        self.family = family
        return self


@dataclass(slots=True)
class SolverConfig:
    solver_type: str
    method: str = "auto"
    seed: Optional[int] = None
    tolerance: float = 1e-8
    maxiter: Optional[int] = None

    def validate(self) -> "SolverConfig":
        solver_type = self.solver_type.lower()
        if solver_type not in SUPPORTED_SOLVER_TYPES:
            raise ConfigError(f"Unsupported solver type: {self.solver_type}")
        if self.tolerance <= 0:
            raise ConfigError("Solver tolerance must be positive.")
        if self.maxiter is not None and self.maxiter <= 0:
            raise ConfigError("Solver maxiter must be positive when provided.")
        if self.seed is not None and self.seed < 0:
            raise ConfigError("Solver seed must be non-negative.")
        self.solver_type = solver_type
        return self


@dataclass(slots=True)
class VQEConfig:
    ansatz_name: str = "hardware_efficient_nn"
    ansatz_depth: int = 2
    optimizer_name: str = "L-BFGS-B"
    maxiter: int = 200
    tol: float = 1e-8
    seed: int = 0
    initial_state_mode: str = "neel"

    def validate(self) -> "VQEConfig":
        if self.ansatz_depth <= 0:
            raise ConfigError("VQE ansatz_depth must be positive.")
        if self.maxiter <= 0:
            raise ConfigError("VQE maxiter must be positive.")
        if self.tol <= 0:
            raise ConfigError("VQE tol must be positive.")
        if self.seed < 0:
            raise ConfigError("VQE seed must be non-negative.")
        return self


@dataclass(slots=True)
class ExactStateConfig:
    method: str = "auto"
    dense_qubit_threshold: int = 12
    which: str = "SA"
    k: int = 1
    tol: float = 1e-10
    maxiter: Optional[int] = None

    def validate(self) -> "ExactStateConfig":
        method = self.method.lower()
        if method not in SUPPORTED_EXACT_METHODS:
            raise ConfigError(f"Unsupported exact-state method: {self.method}")
        if self.dense_qubit_threshold <= 1:
            raise ConfigError("dense_qubit_threshold must be greater than 1.")
        if self.k != 1:
            raise ConfigError("Only k=1 ground-state extraction is supported in v1.")
        if self.tol <= 0:
            raise ConfigError("Exact-state tol must be positive.")
        if self.maxiter is not None and self.maxiter <= 0:
            raise ConfigError("Exact-state maxiter must be positive when provided.")
        self.method = method
        return self


@dataclass(slots=True)
class CircuitConfig:
    depth_d: int
    rx_angles: Optional[Sequence[float]] = None
    rz_angles: Optional[Sequence[float]] = None
    rzz_angles: Optional[Sequence[float]] = None
    angle_generation_rule: Optional[Dict[str, Any]] = None

    def validate(self, num_qubits: int) -> "CircuitConfig":
        if self.depth_d < 0:
            raise ConfigError("Circuit depth_d must be non-negative.")
        if self.rx_angles is None and self.angle_generation_rule is None:
            raise ConfigError("Either explicit circuit angles or angle_generation_rule must be provided.")
        if self.angle_generation_rule is None:
            _validate_angle_lengths(num_qubits, self.rx_angles, self.rz_angles, self.rzz_angles)
        return self


@dataclass(slots=True)
class RuntimeConfig:
    mq_backend_name: str = "mqvector"
    dtype: str = "complex128"
    max_qubits: int = 20
    threads: Optional[int] = None

    def validate(self) -> "RuntimeConfig":
        if self.dtype not in SUPPORTED_DTYPES:
            raise ConfigError(f"Unsupported runtime dtype: {self.dtype}")
        if self.max_qubits <= 1:
            raise ConfigError("max_qubits must be greater than 1.")
        if self.threads is not None and self.threads <= 0:
            raise ConfigError("threads must be positive when provided.")
        return self


@dataclass(slots=True)
class OutputConfig:
    output_dir: str
    save_final_statevector: bool = False
    schema_version: str = "py-mq-v1"

    def validate(self) -> "OutputConfig":
        if not self.output_dir:
            raise ConfigError("output_dir must be provided.")
        return self

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir)


@dataclass(slots=True)
class WorkflowConfig:
    hamiltonian: HamiltonianConfig
    solver: SolverConfig
    circuit: CircuitConfig
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    output: OutputConfig = field(default_factory=lambda: OutputConfig(output_dir="data/python-mq"))
    vqe: Optional[VQEConfig] = None
    exact_state: Optional[ExactStateConfig] = None

    def validate(self) -> "WorkflowConfig":
        self.hamiltonian.validate()
        self.runtime.validate()
        self.output.validate()
        self.solver.validate()
        self._validate_runtime_guardrails()
        self.circuit.validate(self.hamiltonian.N)

        if self.solver.solver_type == "vqe":
            if self.vqe is None:
                self.vqe = VQEConfig()
            self.vqe.validate()
            self.exact_state = None if self.exact_state is None else self.exact_state.validate()
        elif self.solver.solver_type == "exact_state":
            if self.exact_state is None:
                self.exact_state = ExactStateConfig(method=self.solver.method)
            self.exact_state.validate()
            self.vqe = None if self.vqe is None else self.vqe.validate()
        return self

    def _validate_runtime_guardrails(self) -> None:
        if self.hamiltonian.N > self.runtime.max_qubits:
            raise ConfigError(
                f"Requested N={self.hamiltonian.N} exceeds configured max_qubits={self.runtime.max_qubits}."
            )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "WorkflowConfig":
        hamiltonian = HamiltonianConfig(**dict(data.get("hamiltonian", {})))
        solver = SolverConfig(**dict(data.get("solver", {})))
        circuit = CircuitConfig(**dict(data.get("circuit", {})))
        runtime = RuntimeConfig(**dict(data.get("runtime", {})))
        output = OutputConfig(**dict(data.get("output", {})))
        vqe_data = data.get("vqe")
        exact_data = data.get("exact_state")
        return cls(
            hamiltonian=hamiltonian,
            solver=solver,
            circuit=circuit,
            runtime=runtime,
            output=output,
            vqe=VQEConfig(**dict(vqe_data)) if vqe_data is not None else None,
            exact_state=ExactStateConfig(**dict(exact_data)) if exact_data is not None else None,
        ).validate()


def _validate_angle_lengths(
    num_qubits: int,
    rx_angles: Optional[Sequence[float]],
    rz_angles: Optional[Sequence[float]],
    rzz_angles: Optional[Sequence[float]],
) -> None:
    if rx_angles is None or rz_angles is None or rzz_angles is None:
        raise ConfigError("Explicit circuit mode requires rx_angles, rz_angles, and rzz_angles.")
    if len(rx_angles) != num_qubits:
        raise ConfigError(f"rx_angles must have length {num_qubits}.")
    if len(rz_angles) != num_qubits:
        raise ConfigError(f"rz_angles must have length {num_qubits}.")
    if len(rzz_angles) != num_qubits - 1:
        raise ConfigError(f"rzz_angles must have length {num_qubits - 1}.")


def resolve_circuit_angles(config: CircuitConfig, num_qubits: int) -> Dict[str, np.ndarray]:
    """Resolve explicit or seeded-rule circuit angles into arrays."""
    config.validate(num_qubits)
    if config.angle_generation_rule is None:
        return {
            "rx_angles": np.asarray(config.rx_angles, dtype=float),
            "rz_angles": np.asarray(config.rz_angles, dtype=float),
            "rzz_angles": np.asarray(config.rzz_angles, dtype=float),
        }

    rule = dict(config.angle_generation_rule)
    seed = int(rule.get("seed", 0))
    rng = np.random.default_rng(seed)
    g_scalar = float(rule.get("g_scalar", 0.0))
    rz_range = tuple(rule.get("rz_range", (-np.pi, np.pi)))
    rzz_range = tuple(rule.get("rzz_range", (-np.pi, np.pi)))
    if len(rz_range) != 2 or len(rzz_range) != 2:
        raise ConfigError("rz_range and rzz_range must be length-2 ranges.")

    rx_angles = np.full(num_qubits, g_scalar * np.pi, dtype=float)
    rz_angles = rng.uniform(rz_range[0], rz_range[1], size=num_qubits)
    rzz_angles = rng.uniform(rzz_range[0], rzz_range[1], size=num_qubits - 1)
    return {
        "rx_angles": rx_angles,
        "rz_angles": rz_angles,
        "rzz_angles": rzz_angles,
    }
