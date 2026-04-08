"""Run the qrc-phase Python eSSH workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Sequence

from py_backend.compare_itensor import compare_saved_results
from py_backend.config import WorkflowConfig
from py_backend.hamiltonians import build_essh_hamiltonian
from py_backend.io import build_output_directory, save_run_artifacts
from py_backend.repeated_circuit import run_repeated_circuit
from py_backend.solvers import exact_state as exact_state_solver
from py_backend.solvers import vqe as vqe_solver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the qrc-phase Python eSSH workflow.")
    parser.add_argument("--config", type=str, default=None, help="Path to a JSON workflow config file.")
    parser.add_argument("--config-list", type=str, nargs="*", default=None, help="Optional list of JSON workflow config files.")
    parser.add_argument("--output-dir", type=str, default=None, help="Optional explicit output directory override.")
    parser.add_argument("--compare-to", type=str, default=None, help="Optional reference result path for observable-level comparison.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop batch execution after the first failure.")
    return parser.parse_args()


def load_config(path: str) -> WorkflowConfig:
    data: Dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return WorkflowConfig.from_dict(data)


def resolve_config_paths(args: argparse.Namespace) -> list[str]:
    paths: list[str] = []
    if args.config is not None:
        paths.append(args.config)
    if args.config_list:
        paths.extend(args.config_list)
    if not paths:
        raise ValueError("At least one workflow config file must be provided with --config or --config-list.")
    return paths


def run_single_workflow(
    workflow: WorkflowConfig,
    output_dir_override: str | None = None,
    compare_to: str | None = None,
) -> dict[str, Any]:
    hamiltonian_bundle = build_essh_hamiltonian(workflow.hamiltonian)
    if workflow.solver.solver_type == "vqe":
        prepared = vqe_solver.solve_ground_state(
            hamiltonian_bundle,
            workflow.solver,
            workflow.runtime,
            workflow.vqe,
        )
    elif workflow.solver.solver_type == "exact_state":
        prepared = exact_state_solver.solve_ground_state(
            hamiltonian_bundle,
            workflow.solver,
            workflow.runtime,
            workflow.exact_state,
        )
    else:  # pragma: no cover
        raise ValueError(f"Unsupported solver type: {workflow.solver.solver_type}")

    trajectory = run_repeated_circuit(
        prepared,
        workflow.circuit,
        workflow.runtime,
        save_final_statevector=workflow.output.save_final_statevector,
    )
    output_dir = resolve_output_dir(workflow, output_dir_override)
    saved_dir = save_run_artifacts(workflow.output, workflow, prepared, trajectory, output_dir=output_dir)
    summary: dict[str, Any] = {
        "output_dir": str(saved_dir),
        "solver_type": prepared.solver_type,
        "solver_method": prepared.solver_method,
        "energy": float(prepared.energy),
    }
    if compare_to is not None:
        summary["comparison"] = compare_saved_results(compare_to, saved_dir)
    return summary


def run_batch(
    config_paths: Sequence[str],
    output_dir_override: str | None = None,
    fail_fast: bool = False,
    compare_to: str | None = None,
) -> dict[str, Any]:
    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    for config_path in config_paths:
        try:
            workflow = load_config(config_path)
            run_summary = run_single_workflow(
                workflow,
                output_dir_override=output_dir_override,
                compare_to=compare_to,
            )
            successes.append({"config": str(config_path), **run_summary})
        except Exception as exc:
            failures.append({"config": str(config_path), "error": str(exc)})
            if fail_fast:
                break
    return {"successes": successes, "failures": failures}


def resolve_output_dir(workflow: WorkflowConfig, output_dir_override: str | None) -> Path:
    """Resolve the final output directory, preserving canonical subdirectories under an override root."""
    canonical_dir = build_output_directory(workflow)
    if output_dir_override is None:
        return canonical_dir
    override_root = Path(output_dir_override)
    base_root = Path(workflow.output.output_dir)
    try:
        relative_dir = canonical_dir.relative_to(base_root)
    except ValueError:
        relative_dir = canonical_dir
    return override_root / relative_dir


def main() -> None:
    args = parse_args()
    summary = run_batch(
        resolve_config_paths(args),
        output_dir_override=args.output_dir,
        fail_fast=args.fail_fast,
        compare_to=args.compare_to,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
