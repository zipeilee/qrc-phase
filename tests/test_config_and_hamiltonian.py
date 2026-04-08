"""Unit tests for qrc-phase configuration and Hamiltonian helpers."""

from __future__ import annotations

import numpy as np

from py_backend.config import CircuitConfig, ExactStateConfig, HamiltonianConfig, RuntimeConfig, SolverConfig, WorkflowConfig, resolve_circuit_angles
from py_backend.hamiltonians import build_essh_hamiltonian
from py_backend.solvers import exact_state as exact_state_solver


def test_resolve_circuit_angles_seeded_rule_is_deterministic() -> None:
    config = CircuitConfig(
        depth_d=2,
        angle_generation_rule={
            "seed": 123,
            "g_scalar": 0.84,
            "rz_range": [-1.0, 1.0],
            "rzz_range": [-2.0, 2.0],
        },
    )
    first = resolve_circuit_angles(config, 4)
    second = resolve_circuit_angles(config, 4)
    assert np.allclose(first["rx_angles"], second["rx_angles"])
    assert np.allclose(first["rz_angles"], second["rz_angles"])
    assert np.allclose(first["rzz_angles"], second["rzz_angles"])


def test_workflow_guardrail_rejects_oversized_qubit_count() -> None:
    try:
        WorkflowConfig.from_dict(
            {
                "hamiltonian": {"family": "essh", "N": 21, "J1": 1.0, "J2": 0.5, "delta": 0.0},
                "solver": {"solver_type": "exact_state", "method": "auto"},
                "circuit": {
                    "depth_d": 1,
                    "rx_angles": [0.1] * 21,
                    "rz_angles": [0.2] * 21,
                    "rzz_angles": [0.3] * 20,
                },
                "output": {"output_dir": "data/python-mq"},
            }
        )
    except ValueError as exc:
        assert "max_qubits" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected oversized-qubit workflow config to fail.")


def test_essh_hamiltonian_matrix_properties() -> None:
    config = HamiltonianConfig(family="essh", N=4, J1=1.0, J2=0.5, delta=0.25)
    bundle = build_essh_hamiltonian(config)
    dense = bundle.get_dense_matrix()
    assert dense.shape == (16, 16)
    assert np.allclose(dense, dense.conj().T)
    assert bundle.sparse_matrix.nnz > 0


def test_exact_state_solver_returns_normalized_ground_state() -> None:
    bundle = build_essh_hamiltonian(HamiltonianConfig(family="essh", N=4, J1=1.0, J2=0.5, delta=0.25))
    prepared = exact_state_solver.solve_ground_state(
        bundle,
        SolverConfig(solver_type="exact_state", method="dense_eigh", seed=3),
        RuntimeConfig(max_qubits=8),
        ExactStateConfig(method="dense_eigh", dense_qubit_threshold=8),
    )
    assert prepared.solver_type == "exact_state"
    assert prepared.solver_method == "dense_eigh"
    assert prepared.statevector.shape == (16,)
    assert np.isclose(np.linalg.norm(prepared.statevector), 1.0)
    assert "selected_method" in prepared.solver_summary
