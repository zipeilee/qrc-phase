"""Observable extraction for qrc-phase Python workflows."""

from __future__ import annotations

from typing import List, Sequence

import numpy as np

from .mq_adapter import build_hamiltonian_from_term, get_expectation


def build_observable_order(num_qubits: int) -> List[str]:
    """Return the canonical observable ordering used by the legacy notebooks."""
    if num_qubits <= 1:
        raise ValueError("num_qubits must be greater than 1.")
    singles = [f"Z_{i + 1}" for i in range(num_qubits)]
    pairs = [f"ZZ_{i + 1},{i + 2}" for i in range(num_qubits - 1)]
    return singles + pairs


def build_observable_terms(num_qubits: int) -> List[str]:
    """Return canonical Pauli terms matching the observable order."""
    if num_qubits <= 1:
        raise ValueError("num_qubits must be greater than 1.")
    singles = [f"Z{i}" for i in range(num_qubits)]
    pairs = [f"Z{i} Z{i + 1}" for i in range(num_qubits - 1)]
    return singles + pairs


def measure_embedding_snapshot(simulator: object, num_qubits: int) -> np.ndarray:
    """Measure Z and nearest-neighbor ZZ observables on the current simulator state."""
    values: list[float] = []
    for term in build_observable_terms(num_qubits):
        value = get_expectation(simulator, build_hamiltonian_from_term(term))
        values.append(float(np.real(value)))
    return np.asarray(values, dtype=float)


def stack_embedding_snapshots(snapshots: Sequence[np.ndarray]) -> np.ndarray:
    """Stack per-time snapshots into the canonical embedding matrix shape (2N-1, d+1)."""
    if not snapshots:
        raise ValueError("snapshots must be non-empty.")
    normalized = [np.asarray(snapshot, dtype=float).reshape(-1) for snapshot in snapshots]
    first_shape = normalized[0].shape
    for snapshot in normalized[1:]:
        if snapshot.shape != first_shape:
            raise ValueError("All snapshots must share the same shape.")
    return np.stack(normalized, axis=1)
