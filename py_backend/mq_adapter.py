"""Lazy MindQuantum/MindSpore integration helpers for qrc-phase."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Iterable, Sequence, Tuple

import numpy as np


class MindQuantumUnavailable(ImportError):
    """Raised when MindQuantum or its required runtime is unavailable."""


@lru_cache(maxsize=1)
def load_mq() -> Dict[str, Any]:
    """Load MindQuantum symbols lazily so package import stays lightweight."""
    try:
        from mindquantum.core.circuit import Circuit
        from mindquantum.core.gates import Rzz
        from mindquantum.core.operators import Hamiltonian, QubitOperator
        from mindquantum.simulator import Simulator
    except ImportError as exc:  # pragma: no cover - exercised only in missing-dependency environments.
        raise MindQuantumUnavailable(
            "MindQuantum backend is unavailable. Install `mindspore` and `mindquantum` to use this workflow."
        ) from exc

    return {
        "Circuit": Circuit,
        "Hamiltonian": Hamiltonian,
        "QubitOperator": QubitOperator,
        "Rzz": Rzz,
        "Simulator": Simulator,
    }


def build_qubit_operator(pauli_terms: Iterable[Tuple[str, float]]) -> Any:
    """Construct a MindQuantum QubitOperator from explicit Pauli-string terms."""
    mq = load_mq()
    operator = mq["QubitOperator"]()
    for term, coefficient in pauli_terms:
        operator += mq["QubitOperator"](term, coefficient)
    return operator


def build_hamiltonian_from_operator(qubit_operator: Any) -> Any:
    """Wrap a MindQuantum QubitOperator into a Hamiltonian object."""
    mq = load_mq()
    return mq["Hamiltonian"](qubit_operator)


def build_hamiltonian_from_term(term: str, coefficient: float = 1.0) -> Any:
    """Convenience helper for a single-term Hamiltonian."""
    return build_hamiltonian_from_operator(build_qubit_operator([(term, coefficient)]))


def create_circuit() -> Any:
    """Create an empty MindQuantum circuit."""
    return load_mq()["Circuit"]()


def create_simulator(
    num_qubits: int,
    backend: str = "mqvector",
    seed: int | None = None,
    threads: int | None = None,
) -> Any:
    """Create a MindQuantum simulator instance and apply optional thread settings."""
    simulator = load_mq()["Simulator"](backend, num_qubits, seed=seed)
    if threads is not None:
        simulator.set_threads_number(int(threads))
    return simulator


def get_statevector(simulator: Any) -> np.ndarray:
    """Extract a complex128 statevector from a MindQuantum simulator."""
    return np.asarray(simulator.get_qs(), dtype=np.complex128)


def set_statevector(simulator: Any, statevector: Sequence[complex]) -> None:
    """Inject a statevector into a MindQuantum simulator."""
    simulator.set_qs(np.asarray(statevector, dtype=np.complex128))


def get_expectation(simulator: Any, hamiltonian: Any) -> complex:
    """Get the expectation value of a Hamiltonian on the simulator state."""
    return complex(simulator.get_expectation(hamiltonian))


def create_neel_preparation_circuit(num_qubits: int) -> Any:
    """Create the |0101...> preparation circuit matching the Julia Neel initialization."""
    circuit = create_circuit()
    for qubit in range(num_qubits):
        if qubit % 2 == 1:
            circuit.x(qubit)
    return circuit


def apply_rx_layer(circuit: Any, angles: Sequence[float]) -> Any:
    """Append an all-qubit RX layer."""
    for qubit, angle in enumerate(angles):
        circuit.rx(float(angle), qubit)
    return circuit


def apply_ry_layer(circuit: Any, angles: Sequence[float]) -> Any:
    """Append an all-qubit RY layer."""
    for qubit, angle in enumerate(angles):
        circuit.ry(float(angle), qubit)
    return circuit


def apply_rz_layer(circuit: Any, angles: Sequence[float]) -> Any:
    """Append an all-qubit RZ layer."""
    for qubit, angle in enumerate(angles):
        circuit.rz(float(angle), qubit)
    return circuit


def apply_rzz_layer(circuit: Any, angles: Sequence[float]) -> Any:
    """Append a nearest-neighbor Rzz layer."""
    gate_class = load_mq()["Rzz"]
    for qubit, angle in enumerate(angles):
        circuit += gate_class(float(angle)).on([qubit, qubit + 1])
    return circuit


def expectation_with_grad(simulator: Any, hamiltonian: Any, circuit: Any):
    """Create the expectation-with-gradient callable used by VQE."""
    return simulator.get_expectation_with_grad(hamiltonian, circuit)


def flatten_grad_result(forward: Any, gradient: Any) -> tuple[float, np.ndarray]:
    """Normalize MindQuantum grad-op outputs into SciPy-friendly arrays."""
    value = float(np.real(np.asarray(forward).reshape(-1)[0]))
    grad = np.real(np.asarray(gradient)).reshape(-1).astype(float)
    return value, grad
