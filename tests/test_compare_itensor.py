"""Unit tests for comparison helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from py_backend.compare_itensor import compare_embedding_matrices, compare_saved_results


def test_compare_embedding_matrices_reports_zero_for_equal_inputs() -> None:
    left = np.array([[1.0, 2.0], [3.0, 4.0]])
    right = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = compare_embedding_matrices(left, right)
    assert result.shape_match is True
    assert result.max_abs_diff == 0.0
    assert result.mean_abs_diff == 0.0


def test_compare_embedding_matrices_detects_shape_mismatch() -> None:
    left = np.zeros((2, 2))
    right = np.zeros((2, 3))
    result = compare_embedding_matrices(left, right)
    assert result.shape_match is False


def test_compare_saved_results_reports_energy_and_t0_diffs(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    candidate_dir = tmp_path / "candidate"
    reference_dir.mkdir()
    candidate_dir.mkdir()
    reference_embedding = np.array([[1.0, 0.5], [0.0, -0.5], [0.25, 0.75]])
    candidate_embedding = np.array([[1.1, 0.5], [0.1, -0.4], [0.0, 0.75]])
    np.savez_compressed(reference_dir / "result.npz", embedding_matrix=reference_embedding, ground_state_energy=np.array([-1.2]))
    np.savez_compressed(candidate_dir / "result.npz", embedding_matrix=candidate_embedding, ground_state_energy=np.array([-1.1]))
    (reference_dir / "metadata.json").write_text(
        json.dumps({"solver": {"solver_type": "exact_state", "solver_method": "dense_eigh"}}),
        encoding="utf-8",
    )
    (candidate_dir / "metadata.json").write_text(
        json.dumps({"solver": {"solver_type": "vqe", "solver_method": "L-BFGS-B"}}),
        encoding="utf-8",
    )

    summary = compare_saved_results(reference_dir, candidate_dir)
    assert summary["shape_match"] is True
    assert summary["energy_abs_diff"] == 0.1
    assert summary["t0_z_max_abs_diff"] == 0.1
    assert summary["t0_zz_max_abs_diff"] == 0.25
    assert summary["reference_solver"]["solver_type"] == "exact_state"
    assert summary["candidate_solver"]["solver_type"] == "vqe"
