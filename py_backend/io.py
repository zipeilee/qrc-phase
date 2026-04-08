"""Persistence helpers for qrc-phase Python workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np

from .config import OutputConfig, WorkflowConfig
from .repeated_circuit import TrajectoryResult
from .solvers.base import PreparedState


RESULT_ARCHIVE_NAME = "result.npz"
METADATA_NAME = "metadata.json"


def build_output_directory(workflow: WorkflowConfig) -> Path:
    """Construct a stable output directory path from workflow metadata."""
    h = workflow.hamiltonian
    solver = workflow.solver
    seed = solver.seed if solver.seed is not None else 0
    method = solver.method or solver.solver_type
    path = (
        Path(workflow.output.output_dir)
        / h.family
        / f"N{h.N}"
        / f"delta_{_fmt(h.delta)}"
        / f"J2_{_fmt(h.J2)}"
        / f"{solver.solver_type}_{method}"
        / f"d{workflow.circuit.depth_d}_seed{seed}"
    )
    return path


def save_run_artifacts(
    output_config: OutputConfig,
    workflow: WorkflowConfig,
    prepared: PreparedState,
    trajectory: TrajectoryResult,
    output_dir: Path | None = None,
) -> Path:
    """Persist canonical NPZ and JSON artifacts for one workflow run."""
    target_dir = Path(output_dir) if output_dir is not None else build_output_directory(workflow)
    target_dir.mkdir(parents=True, exist_ok=True)

    archive_path = target_dir / RESULT_ARCHIVE_NAME
    npz_payload: Dict[str, Any] = {
        "embedding_matrix": np.asarray(trajectory.embedding_matrix, dtype=float),
        "rx_angles": np.asarray(trajectory.circuit_params["rx_angles"], dtype=float),
        "rz_angles": np.asarray(trajectory.circuit_params["rz_angles"], dtype=float),
        "rzz_angles": np.asarray(trajectory.circuit_params["rzz_angles"], dtype=float),
        "time_steps": np.asarray(trajectory.time_steps, dtype=int),
        "observable_order": np.asarray(trajectory.observable_order, dtype=object),
        "ground_state_energy": np.asarray([prepared.energy], dtype=float),
    }
    if output_config.save_final_statevector and trajectory.final_statevector is not None:
        npz_payload["final_statevector"] = np.asarray(trajectory.final_statevector, dtype=np.complex128)
    np.savez_compressed(archive_path, **npz_payload)

    metadata = build_metadata(output_config, workflow, prepared, trajectory, archive_path)
    metadata_path = target_dir / METADATA_NAME
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return target_dir


def build_metadata(
    output_config: OutputConfig,
    workflow: WorkflowConfig,
    prepared: PreparedState,
    trajectory: TrajectoryResult,
    archive_path: Path,
) -> Dict[str, Any]:
    """Build structured JSON metadata for downstream analysis and comparison."""
    return {
        "schema_version": output_config.schema_version,
        "result_archive": archive_path.name,
        "output_directory": str(archive_path.parent),
        "hamiltonian": dict(prepared.hamiltonian_params),
        "solver": {
            "solver_type": prepared.solver_type,
            "solver_method": prepared.solver_method,
            "requested_method": workflow.solver.method,
            "backend": prepared.backend,
            "seed": prepared.seed,
            "summary": _to_jsonable(prepared.solver_summary),
        },
        "runtime": {
            "mq_backend_name": workflow.runtime.mq_backend_name,
            "dtype": workflow.runtime.dtype,
            "max_qubits": workflow.runtime.max_qubits,
            "threads": workflow.runtime.threads,
        },
        "circuit": {
            "depth_d": workflow.circuit.depth_d,
            "rx_angles": trajectory.circuit_params["rx_angles"].tolist(),
            "rz_angles": trajectory.circuit_params["rz_angles"].tolist(),
            "rzz_angles": trajectory.circuit_params["rzz_angles"].tolist(),
            "angle_generation_rule": workflow.circuit.angle_generation_rule,
        },
        "trajectory": {
            "embedding_shape": list(map(int, trajectory.embedding_matrix.shape)),
            "observable_order": list(trajectory.observable_order),
            "time_steps": list(map(int, trajectory.time_steps)),
            "initial_energy": float(trajectory.initial_energy),
            "saved_final_statevector": bool(output_config.save_final_statevector and trajectory.final_statevector is not None),
            "metadata": _to_jsonable(trajectory.metadata),
        },
    }


def _fmt(value: float) -> str:
    return f"{value:.6f}".replace("-", "m")


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, complex):
        return {"real": float(np.real(value)), "imag": float(np.imag(value))}
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value
