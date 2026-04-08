"""Unit tests for qrc-phase IO helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from py_backend.config import WorkflowConfig
from py_backend.io import build_output_directory, save_run_artifacts
from py_backend.repeated_circuit import TrajectoryResult
from py_backend.solvers.base import PreparedState


def _make_workflow(tmp_path: Path) -> WorkflowConfig:
    return WorkflowConfig.from_dict(
        {
            "hamiltonian": {"family": "essh", "N": 4, "J1": 1.0, "J2": 0.5, "delta": 0.25},
            "solver": {"solver_type": "exact_state", "method": "dense_eigh", "seed": 7},
            "circuit": {
                "depth_d": 2,
                "rx_angles": [0.1, 0.2, 0.3, 0.4],
                "rz_angles": [0.5, 0.6, 0.7, 0.8],
                "rzz_angles": [0.9, 1.0, 1.1],
            },
            "output": {"output_dir": str(tmp_path), "save_final_statevector": True},
        }
    )


def test_save_run_artifacts_writes_npz_and_metadata(tmp_path: Path) -> None:
    workflow = _make_workflow(tmp_path)
    prepared = PreparedState(
        solver_type="exact_state",
        solver_method="dense_eigh",
        backend="scipy",
        num_qubits=4,
        hamiltonian_family="essh",
        hamiltonian_params={
            "family": "essh",
            "N": 4,
            "J1": 1.0,
            "J2": 0.5,
            "delta": 0.25,
            "periodic": False,
            "penalty_z1": 0.01,
        },
        energy=-1.234,
        statevector=np.zeros(16, dtype=np.complex128),
        solver_summary={"selected_method": "dense_eigh"},
        seed=7,
    )
    prepared.statevector[0] = 1.0 + 0.0j
    trajectory = TrajectoryResult(
        embedding_matrix=np.zeros((7, 3), dtype=float),
        observable_order=["Z_1", "Z_2", "Z_3", "Z_4", "ZZ_1,2", "ZZ_2,3", "ZZ_3,4"],
        time_steps=[0, 1, 2],
        circuit_params={
            "rx_angles": np.array([0.1, 0.2, 0.3, 0.4]),
            "rz_angles": np.array([0.5, 0.6, 0.7, 0.8]),
            "rzz_angles": np.array([0.9, 1.0, 1.1]),
        },
        initial_energy=-1.234,
        solver_type="exact_state",
        solver_method="dense_eigh",
        final_statevector=np.ones(16, dtype=np.complex128) / 4.0,
        metadata={"includes_t0": True},
    )
    output_dir = build_output_directory(workflow)
    saved_dir = save_run_artifacts(workflow.output, workflow, prepared, trajectory, output_dir=output_dir)
    archive_path = saved_dir / "result.npz"
    metadata_path = saved_dir / "metadata.json"
    assert archive_path.exists()
    assert metadata_path.exists()
    with np.load(archive_path, allow_pickle=True) as data:
        assert data["embedding_matrix"].shape == (7, 3)
        assert data["final_statevector"].shape == (16,)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["trajectory"]["embedding_shape"] == [7, 3]
    assert metadata["solver"]["solver_type"] == "exact_state"
