"""Common solver contracts for qrc-phase Python workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol

import numpy as np


class SolverFailure(RuntimeError):
    """Raised when a ground-state solver cannot produce a valid result."""


@dataclass(slots=True)
class PreparedState:
    solver_type: str
    solver_method: str
    backend: str
    num_qubits: int
    hamiltonian_family: str
    hamiltonian_params: Dict[str, Any]
    energy: float
    statevector: np.ndarray
    solver_summary: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[int] = None

    def validate(self) -> "PreparedState":
        expected_dim = 1 << self.num_qubits
        if self.statevector.shape != (expected_dim,):
            raise SolverFailure(
                f"Statevector shape {self.statevector.shape} does not match expected dimension {(expected_dim,)}."
            )
        norm = float(np.linalg.norm(self.statevector))
        if not np.isfinite(norm) or norm == 0.0:
            raise SolverFailure("Statevector norm is invalid.")
        if not np.isclose(norm, 1.0, atol=1e-8):
            self.statevector = self.statevector / norm
        return self


class GroundStateSolver(Protocol):
    def solve_ground_state(self, *args: Any, **kwargs: Any) -> PreparedState:
        """Compute a ground state and return a normalized shared contract."""
