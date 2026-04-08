"""VQE solver implementation for qrc-phase."""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np
from scipy.optimize import minimize

from ..config import RuntimeConfig, SolverConfig, VQEConfig
from ..hamiltonians import HamiltonianBundle
from ..mq_adapter import (
    create_neel_preparation_circuit,
    create_simulator,
    expectation_with_grad,
    flatten_grad_result,
    get_statevector,
)
from .base import PreparedState, SolverFailure


def solve_ground_state(
    hamiltonian_bundle: HamiltonianBundle,
    solver_config: SolverConfig,
    runtime_config: RuntimeConfig,
    vqe_config: VQEConfig,
) -> PreparedState:
    """Run a MindQuantum-based VQE optimization and return a PreparedState."""
    if hamiltonian_bundle.mq_hamiltonian is None:
        raise SolverFailure(
            "VQE requires MindQuantum Hamiltonian support. Install `mindspore` and `mindquantum` to use solver_type='vqe'."
        )

    circuit, parameter_names = build_vqe_circuit(hamiltonian_bundle.num_qubits, vqe_config)
    param_count = len(parameter_names)
    rng_seed = solver_config.seed if solver_config.seed is not None else vqe_config.seed
    rng = np.random.default_rng(rng_seed)
    initial_params = rng.uniform(-0.1, 0.1, size=param_count)
    simulator = create_simulator(
        hamiltonian_bundle.num_qubits,
        backend=runtime_config.mq_backend_name,
        seed=solver_config.seed,
        threads=runtime_config.threads,
    )
    grad_ops = expectation_with_grad(simulator, hamiltonian_bundle.mq_hamiltonian, circuit)

    def objective(parameters: np.ndarray) -> Tuple[float, np.ndarray]:
        forward, gradient = grad_ops(np.asarray(parameters, dtype=float))
        return flatten_grad_result(forward, gradient)

    def fun(parameters: np.ndarray) -> float:
        value, _ = objective(parameters)
        return value

    def jac(parameters: np.ndarray) -> np.ndarray:
        _, grad = objective(parameters)
        return grad

    result = minimize(
        fun=fun,
        x0=initial_params,
        jac=jac,
        method=vqe_config.optimizer_name,
        tol=min(vqe_config.tol, solver_config.tolerance),
        options={"maxiter": vqe_config.maxiter if solver_config.maxiter is None else solver_config.maxiter},
    )
    if not result.success:
        raise SolverFailure(f"VQE did not converge: {result.message}")

    final_value, final_grad = objective(result.x)
    final_sim = create_simulator(
        hamiltonian_bundle.num_qubits,
        backend=runtime_config.mq_backend_name,
        seed=solver_config.seed,
        threads=runtime_config.threads,
    )
    final_sim.apply_circuit(circuit, result.x)
    statevector = get_statevector(final_sim)
    summary: Dict[str, Any] = {
        "final_energy": float(final_value),
        "initial_params": initial_params.tolist(),
        "optimized_params": result.x.tolist(),
        "optimizer_name": vqe_config.optimizer_name,
        "iterations": int(getattr(result, "nit", 0)),
        "converged": bool(result.success),
        "final_gradient_norm": float(np.linalg.norm(final_grad)),
        "parameter_names": parameter_names,
        "message": str(result.message),
        "ansatz_name": vqe_config.ansatz_name,
        "ansatz_depth": vqe_config.ansatz_depth,
        "initial_state_mode": vqe_config.initial_state_mode,
        "seed": rng_seed,
    }
    prepared = PreparedState(
        solver_type="vqe",
        solver_method=vqe_config.optimizer_name,
        backend="mindquantum",
        num_qubits=hamiltonian_bundle.num_qubits,
        hamiltonian_family=hamiltonian_bundle.family,
        hamiltonian_params=dict(hamiltonian_bundle.params),
        energy=float(final_value),
        statevector=statevector,
        solver_summary=summary,
        seed=rng_seed,
    )
    return prepared.validate()


def build_vqe_circuit(num_qubits: int, vqe_config: VQEConfig) -> Tuple[Any, list[str]]:
    """Construct the fixed preparation circuit plus parameterized hardware-efficient ansatz."""
    if vqe_config.initial_state_mode != "neel":
        raise SolverFailure(f"Unsupported VQE initial_state_mode: {vqe_config.initial_state_mode}")
    circuit = create_neel_preparation_circuit(num_qubits)
    parameter_names: list[str] = []
    for layer in range(vqe_config.ansatz_depth):
        for qubit in range(num_qubits):
            ry_name = f"theta_ry_{layer}_{qubit}"
            rz_name = f"theta_rz_{layer}_{qubit}"
            circuit.ry(ry_name, qubit)
            circuit.rz(rz_name, qubit)
            parameter_names.extend([ry_name, rz_name])
        for start in (0, 1):
            for qubit in range(start, num_qubits - 1, 2):
                circuit.x(qubit + 1, qubit)
    return circuit, parameter_names
