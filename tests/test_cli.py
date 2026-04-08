"""Unit tests for CLI workflow helpers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_py_essh import load_config, resolve_output_dir


def test_load_config_parses_exact_state_workflow(tmp_path: Path) -> None:
    config_path = tmp_path / "workflow.json"
    config_path.write_text(
        json.dumps(
            {
                "hamiltonian": {"family": "essh", "N": 4, "J1": 1.0, "J2": 0.5, "delta": 0.25},
                "solver": {"solver_type": "exact_state", "method": "auto", "seed": 5},
                "circuit": {
                    "depth_d": 2,
                    "rx_angles": [0.1, 0.2, 0.3, 0.4],
                    "rz_angles": [0.5, 0.6, 0.7, 0.8],
                    "rzz_angles": [0.9, 1.0, 1.1],
                },
                "output": {"output_dir": str(tmp_path / "runs")},
            }
        ),
        encoding="utf-8",
    )

    workflow = load_config(str(config_path))
    assert workflow.solver.solver_type == "exact_state"
    assert workflow.exact_state is not None
    assert workflow.exact_state.method == "auto"


def test_resolve_output_dir_preserves_canonical_suffix_under_override(tmp_path: Path) -> None:
    config_path = tmp_path / "workflow.json"
    config_path.write_text(
        json.dumps(
            {
                "hamiltonian": {"family": "essh", "N": 4, "J1": 1.0, "J2": 0.5, "delta": 0.25},
                "solver": {"solver_type": "exact_state", "method": "dense_eigh", "seed": 2},
                "circuit": {
                    "depth_d": 3,
                    "rx_angles": [0.1, 0.2, 0.3, 0.4],
                    "rz_angles": [0.5, 0.6, 0.7, 0.8],
                    "rzz_angles": [0.9, 1.0, 1.1],
                },
                "output": {"output_dir": str(tmp_path / "default_root")},
            }
        ),
        encoding="utf-8",
    )

    workflow = load_config(str(config_path))
    resolved = resolve_output_dir(workflow, str(tmp_path / "override_root"))
    assert str(resolved).startswith(str(tmp_path / "override_root"))
    assert "d3_seed2" in str(resolved)
