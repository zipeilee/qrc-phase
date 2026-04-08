"""Hamiltonian construction for qrc-phase Python workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix, kron

from .config import HamiltonianConfig
from .mq_adapter import MindQuantumUnavailable, build_hamiltonian_from_operator, build_qubit_operator

PAULI_MATRICES = {
    "I": csr_matrix(np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.complex128)),
    "X": csr_matrix(np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)),
    "Y": csr_matrix(np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)),
    "Z": csr_matrix(np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)),
}


@dataclass(slots=True)
class HamiltonianBundle:
    family: str
    num_qubits: int
    params: Dict[str, Any]
    pauli_terms: List[Tuple[str, float]]
    sparse_matrix: csr_matrix
    mq_hamiltonian: Any | None = None
    qubit_operator: Any | None = None
    dense_matrix: Optional[np.ndarray] = None

    def get_dense_matrix(self) -> np.ndarray:
        """Materialize and cache the dense Hamiltonian matrix."""
        if self.dense_matrix is None:
            self.dense_matrix = self.sparse_matrix.toarray().astype(np.complex128, copy=False)
        return self.dense_matrix


def build_essh_hamiltonian(config: HamiltonianConfig) -> HamiltonianBundle:
    """Build the eSSH Hamiltonian in sparse-matrix form plus optional MindQuantum form."""
    config.validate()
    pauli_terms: list[tuple[str, float]] = []
    for i in range(config.N - 1):
        coupling = config.J1 if i % 2 == 0 else config.J2
        pauli_terms.append((f"X{i} X{i + 1}", coupling))
        pauli_terms.append((f"Y{i} Y{i + 1}", coupling))
        pauli_terms.append((f"Z{i} Z{i + 1}", coupling * config.delta))
    pauli_terms.append(("Z0", config.penalty_z1))

    sparse_matrix = build_sparse_operator(pauli_terms, config.N)
    qubit_operator = None
    mq_hamiltonian = None
    try:
        qubit_operator = build_qubit_operator(pauli_terms)
        mq_hamiltonian = build_hamiltonian_from_operator(qubit_operator)
    except MindQuantumUnavailable:
        pass

    params = {
        "family": config.family,
        "N": config.N,
        "J1": config.J1,
        "J2": config.J2,
        "delta": config.delta,
        "periodic": config.periodic,
        "penalty_z1": config.penalty_z1,
    }
    return HamiltonianBundle(
        family=config.family,
        num_qubits=config.N,
        params=params,
        pauli_terms=pauli_terms,
        sparse_matrix=sparse_matrix,
        mq_hamiltonian=mq_hamiltonian,
        qubit_operator=qubit_operator,
    )


def build_sparse_operator(pauli_terms: Iterable[Tuple[str, float]], num_qubits: int) -> csr_matrix:
    """Construct a sparse Hermitian matrix from Pauli-string terms."""
    dimension = 1 << num_qubits
    total = csr_matrix((dimension, dimension), dtype=np.complex128)
    for term, coefficient in pauli_terms:
        total = total + coefficient * pauli_term_to_sparse(term, num_qubits)
    return total.tocsr()


def pauli_term_to_sparse(term: str, num_qubits: int) -> csr_matrix:
    """Convert a Pauli term like ``Z0 Z1`` into a sparse matrix in little-endian order."""
    ops = ["I"] * num_qubits
    stripped = term.strip()
    if stripped:
        for factor in stripped.split():
            pauli = factor[0]
            qubit = int(factor[1:])
            if pauli not in PAULI_MATRICES:
                raise ValueError(f"Unsupported Pauli factor: {factor}")
            if qubit < 0 or qubit >= num_qubits:
                raise ValueError(f"Qubit index out of range in factor: {factor}")
            ops[qubit] = pauli

    matrix = csr_matrix([[1.0 + 0.0j]])
    for op in reversed(ops):
        matrix = kron(matrix, PAULI_MATRICES[op], format="csr")
    return matrix
