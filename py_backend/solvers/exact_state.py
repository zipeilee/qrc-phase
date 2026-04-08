"""Exact-state solver implementation for qrc-phase."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
from scipy.sparse.linalg import eigsh

from ..config import ExactStateConfig, RuntimeConfig, SolverConfig
from ..hamiltonians import HamiltonianBundle
from .base import PreparedState, SolverFailure


def solve_ground_state(
    hamiltonian_bundle: HamiltonianBundle,
    solver_config: SolverConfig,
    runtime_config: RuntimeConfig,
    exact_config: ExactStateConfig,
) -> PreparedState:
    """Compute the exact or Krylov-style ground state and return a PreparedState."""
    if hamiltonian_bundle.num_qubits > runtime_config.max_qubits:
        raise SolverFailure(
            f"Exact-state solver received N={hamiltonian_bundle.num_qubits}, exceeding max_qubits={runtime_config.max_qubits}."
        )

    method = _resolve_method(hamiltonian_bundle.num_qubits, exact_config)
    try:
        if method == "dense_eigh":
            energy, statevector, summary = _solve_dense(hamiltonian_bundle, exact_config)
        elif method == "sparse_eigsh":
            energy, statevector, summary = _solve_sparse(hamiltonian_bundle, solver_config, exact_config)
        else:
            raise SolverFailure(f"Unsupported resolved exact-state method: {method}")
    except Exception as exc:  # pragma: no cover - exercised in real runtime paths.
        raise SolverFailure(f"Exact-state solver failed with method {method}: {exc}") from exc

    summary["selected_method"] = method
    prepared = PreparedState(
        solver_type="exact_state",
        solver_method=method,
        backend="scipy",
        num_qubits=hamiltonian_bundle.num_qubits,
        hamiltonian_family=hamiltonian_bundle.family,
        hamiltonian_params=dict(hamiltonian_bundle.params),
        energy=float(np.real(energy)),
        statevector=np.asarray(statevector, dtype=np.complex128).reshape(-1),
        solver_summary=summary,
        seed=solver_config.seed,
    )
    return prepared.validate()


def _resolve_method(num_qubits: int, exact_config: ExactStateConfig) -> str:
    if exact_config.method == "auto":
        return "dense_eigh" if num_qubits <= exact_config.dense_qubit_threshold else "sparse_eigsh"
    return exact_config.method


def _solve_dense(
    hamiltonian_bundle: HamiltonianBundle,
    exact_config: ExactStateConfig,
) -> Tuple[float, np.ndarray, Dict[str, Any]]:
    if hamiltonian_bundle.num_qubits > exact_config.dense_qubit_threshold:
        raise SolverFailure(
            "dense_eigh was requested beyond dense_qubit_threshold="
            f"{exact_config.dense_qubit_threshold}. Choose auto or sparse_eigsh instead."
        )
    matrix = hamiltonian_bundle.get_dense_matrix()
    evals, evecs = np.linalg.eigh(matrix)
    energy = evals[0]
    statevector = evecs[:, 0]
    residual = np.linalg.norm(matrix @ statevector - energy * statevector)
    summary = {
        "ground_energy": float(np.real(energy)),
        "residual_norm": float(np.real(residual)),
        "matrix_dimension": int(matrix.shape[0]),
        "nnz": int(hamiltonian_bundle.sparse_matrix.nnz),
        "solver_converged": True,
        "tolerance": exact_config.tol,
    }
    return float(np.real(energy)), statevector, summary


def _solve_sparse(
    hamiltonian_bundle: HamiltonianBundle,
    solver_config: SolverConfig,
    exact_config: ExactStateConfig,
) -> Tuple[float, np.ndarray, Dict[str, Any]]:
    matrix = hamiltonian_bundle.sparse_matrix
    maxiter = exact_config.maxiter if exact_config.maxiter is not None else solver_config.maxiter
    evals, evecs = eigsh(
        matrix,
        k=exact_config.k,
        which=exact_config.which,
        tol=min(exact_config.tol, solver_config.tolerance),
        maxiter=maxiter,
    )
    order = np.argsort(np.real(evals))
    energy = float(np.real(evals[order[0]]))
    statevector = evecs[:, order[0]]
    residual = np.linalg.norm(matrix @ statevector - energy * statevector)
    summary = {
        "ground_energy": energy,
        "residual_norm": float(np.real(residual)),
        "matrix_dimension": int(matrix.shape[0]),
        "nnz": int(matrix.nnz),
        "solver_converged": True,
        "tolerance": min(exact_config.tol, solver_config.tolerance),
        "which": exact_config.which,
        "maxiter": maxiter,
    }
    return energy, statevector, summary
