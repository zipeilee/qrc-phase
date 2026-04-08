"""Repeated-circuit evolution for qrc-phase Python workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np

from .config import CircuitConfig, RuntimeConfig, resolve_circuit_angles
from .mq_adapter import (
    apply_rx_layer,
    apply_rz_layer,
    apply_rzz_layer,
    create_circuit,
    create_simulator,
    get_statevector,
    set_statevector,
)
from .observables import build_observable_order, measure_embedding_snapshot, stack_embedding_snapshots
from .solvers.base import PreparedState, SolverFailure


@dataclass(slots=True)
class TrajectoryResult:
    embedding_matrix: np.ndarray
    observable_order: list[str]
    time_steps: list[int]
    circuit_params: Dict[str, np.ndarray]
    initial_energy: float
    solver_type: str
    solver_method: str
    final_statevector: Optional[np.ndarray]
    metadata: Dict[str, Any] = field(default_factory=dict)


def inject_prepared_state(prepared_state: PreparedState, runtime_config: RuntimeConfig) -> Any:
    """Create a simulator and inject a validated prepared statevector."""
    prepared_state.validate()
    if prepared_state.num_qubits > runtime_config.max_qubits:
        raise SolverFailure(
            f"Prepared state uses {prepared_state.num_qubits} qubits, exceeding runtime max_qubits={runtime_config.max_qubits}."
        )
    statevector = np.asarray(prepared_state.statevector, dtype=np.complex128).reshape(-1)
    expected_dim = 1 << prepared_state.num_qubits
    if statevector.shape != (expected_dim,):
        raise SolverFailure(
            f"Prepared statevector shape {statevector.shape} does not match expected {(expected_dim,)}."
        )
    norm = float(np.linalg.norm(statevector))
    if not np.isfinite(norm) or norm == 0.0:
        raise SolverFailure("Prepared statevector norm is invalid.")
    if not np.isclose(norm, 1.0, atol=1e-8):
        statevector = statevector / norm
    simulator = create_simulator(
        prepared_state.num_qubits,
        backend=runtime_config.mq_backend_name,
        seed=prepared_state.seed,
        threads=runtime_config.threads,
    )
    set_statevector(simulator, statevector)
    return simulator


def build_repeated_layer(num_qubits: int, circuit_config: CircuitConfig) -> tuple[Any, Dict[str, np.ndarray]]:
    """Build the single notebook-style repeated layer and return resolved angles."""
    params = resolve_circuit_angles(circuit_config, num_qubits)
    circuit = create_circuit()
    apply_rx_layer(circuit, params["rx_angles"])
    apply_rzz_layer(circuit, params["rzz_angles"])
    apply_rz_layer(circuit, params["rz_angles"])
    return circuit, params


def run_repeated_circuit(
    prepared_state: PreparedState,
    circuit_config: CircuitConfig,
    runtime_config: RuntimeConfig,
    save_final_statevector: bool = False,
) -> TrajectoryResult:
    """Run t=0 measurement plus repeated single-layer evolution for depth d."""
    simulator = inject_prepared_state(prepared_state, runtime_config)
    repeated_layer, circuit_params = build_repeated_layer(prepared_state.num_qubits, circuit_config)

    snapshots = [measure_embedding_snapshot(simulator, prepared_state.num_qubits)]
    time_steps = [0]
    for step in range(1, circuit_config.depth_d + 1):
        simulator.apply_circuit(repeated_layer)
        snapshots.append(measure_embedding_snapshot(simulator, prepared_state.num_qubits))
        time_steps.append(step)

    final_statevector = get_statevector(simulator) if save_final_statevector else None
    metadata = {
        "num_qubits": prepared_state.num_qubits,
        "depth_d": circuit_config.depth_d,
        "observable_count": int(2 * prepared_state.num_qubits - 1),
        "time_point_count": len(time_steps),
        "includes_t0": True,
        "circuit_structure": ["Rx", "Rzz", "Rz"],
        "state_injection": "direct_statevector",
    }
    return TrajectoryResult(
        embedding_matrix=stack_embedding_snapshots(snapshots),
        observable_order=build_observable_order(prepared_state.num_qubits),
        time_steps=time_steps,
        circuit_params={key: np.asarray(value, dtype=float) for key, value in circuit_params.items()},
        initial_energy=float(prepared_state.energy),
        solver_type=prepared_state.solver_type,
        solver_method=prepared_state.solver_method,
        final_statevector=final_statevector,
        metadata=metadata,
    )
