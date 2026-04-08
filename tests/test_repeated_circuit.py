"""Unit tests for repeated-circuit helpers that do not require MindQuantum runtime."""

from __future__ import annotations

import numpy as np
import pytest

from py_backend.config import CircuitConfig, RuntimeConfig
from py_backend.repeated_circuit import inject_prepared_state
from py_backend.solvers.base import PreparedState, SolverFailure


def test_inject_prepared_state_rejects_invalid_shape() -> None:
    prepared = PreparedState(
        solver_type="exact_state",
        solver_method="dense_eigh",
        backend="scipy",
        num_qubits=3,
        hamiltonian_family="essh",
        hamiltonian_params={"family": "essh", "N": 3},
        energy=-1.0,
        statevector=np.array([1.0 + 0.0j, 0.0 + 0.0j]),
        solver_summary={},
        seed=1,
    )
    with pytest.raises(SolverFailure):
        inject_prepared_state(prepared, RuntimeConfig())


def test_circuit_config_explicit_angles_validate_for_chain() -> None:
    config = CircuitConfig(
        depth_d=2,
        rx_angles=[0.1, 0.2, 0.3, 0.4],
        rz_angles=[0.5, 0.6, 0.7, 0.8],
        rzz_angles=[0.9, 1.0, 1.1],
    )
    assert config.validate(4) is config
