"""Comparison helpers against legacy ITensor outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import numpy as np


@dataclass(slots=True)
class ComparisonResult:
    max_abs_diff: float
    mean_abs_diff: float
    shape_match: bool
    reference_shape: tuple[int, ...]
    candidate_shape: tuple[int, ...]


def load_embedding_matrix(path: str | Path) -> np.ndarray:
    """Load an embedding matrix from NPZ or CSV-like text files."""
    path = Path(path)
    if path.is_dir():
        path = path / "result.npz"
    if path.suffix == ".npz":
        with np.load(path, allow_pickle=True) as data:
            if "embedding_matrix" not in data:
                raise ValueError(f"NPZ file does not contain embedding_matrix: {path}")
            return np.asarray(data["embedding_matrix"], dtype=float)
    if path.suffix in {".csv", ".txt"}:
        return np.loadtxt(path, delimiter="," if path.suffix == ".csv" else None)
    raise ValueError(f"Unsupported comparison file format: {path}")


def compare_embedding_matrices(reference: np.ndarray, candidate: np.ndarray) -> ComparisonResult:
    """Compare two embedding matrices with simple absolute-difference metrics."""
    reference = np.asarray(reference, dtype=float)
    candidate = np.asarray(candidate, dtype=float)
    if reference.shape != candidate.shape:
        return ComparisonResult(
            max_abs_diff=float("inf"),
            mean_abs_diff=float("inf"),
            shape_match=False,
            reference_shape=tuple(reference.shape),
            candidate_shape=tuple(candidate.shape),
        )
    diff = np.abs(reference - candidate)
    return ComparisonResult(
        max_abs_diff=float(np.max(diff)),
        mean_abs_diff=float(np.mean(diff)),
        shape_match=True,
        reference_shape=tuple(reference.shape),
        candidate_shape=tuple(candidate.shape),
    )


def compare_saved_results(reference_path: str | Path, candidate_path: str | Path) -> Dict[str, Any]:
    """Load and compare two saved result artifacts."""
    reference_root = Path(reference_path)
    candidate_root = Path(candidate_path)
    reference = load_embedding_matrix(reference_root)
    candidate = load_embedding_matrix(candidate_root)
    result = compare_embedding_matrices(reference, candidate)
    reference_meta = load_metadata(reference_root)
    candidate_meta = load_metadata(candidate_root)
    comparison = {
        "shape_match": result.shape_match,
        "reference_shape": list(result.reference_shape),
        "candidate_shape": list(result.candidate_shape),
        "max_abs_diff": result.max_abs_diff,
        "mean_abs_diff": result.mean_abs_diff,
    }
    if result.shape_match:
        reference_z_count = _infer_num_qubits_from_shape(result.reference_shape)
        if reference_z_count is not None:
            comparison["t0_z_max_abs_diff"] = float(np.max(np.abs(reference[:reference_z_count, 0] - candidate[:reference_z_count, 0])))
            comparison["t0_zz_max_abs_diff"] = float(
                np.max(np.abs(reference[reference_z_count:, 0] - candidate[reference_z_count:, 0]))
            )
    reference_energy = extract_energy(reference_root, reference_meta)
    candidate_energy = extract_energy(candidate_root, candidate_meta)
    if reference_energy is not None and candidate_energy is not None:
        comparison["energy_abs_diff"] = float(abs(reference_energy - candidate_energy))
    comparison["reference_solver"] = reference_meta.get("solver", {}) if reference_meta else None
    comparison["candidate_solver"] = candidate_meta.get("solver", {}) if candidate_meta else None
    return comparison


def load_metadata(path: str | Path) -> Dict[str, Any] | None:
    """Load metadata.json next to a result archive when available."""
    path = Path(path)
    metadata_path = path / "metadata.json" if path.is_dir() else path.with_name("metadata.json")
    if not metadata_path.exists():
        return None
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def extract_energy(path: str | Path, metadata: Dict[str, Any] | None) -> float | None:
    """Extract the saved ground-state energy from either NPZ payload or metadata."""
    path = Path(path)
    archive_path = path / "result.npz" if path.is_dir() else path
    if archive_path.suffix == ".npz" and archive_path.exists():
        with np.load(archive_path, allow_pickle=True) as data:
            if "ground_state_energy" in data:
                return float(np.asarray(data["ground_state_energy"]).reshape(-1)[0])
    if metadata is not None:
        trajectory = metadata.get("trajectory", {})
        if "initial_energy" in trajectory:
            return float(trajectory["initial_energy"])
    return None


def _infer_num_qubits_from_shape(shape: tuple[int, ...]) -> int | None:
    if len(shape) != 2:
        return None
    obs_dim = int(shape[0])
    if obs_dim % 2 == 0:
        return None
    return (obs_dim + 1) // 2
