"""Unit tests for qrc-phase observable helpers."""

from __future__ import annotations

import numpy as np

from py_backend.observables import build_observable_order, build_observable_terms, stack_embedding_snapshots


def test_observable_order_has_expected_length_and_labels() -> None:
    order = build_observable_order(4)
    assert len(order) == 7
    assert order[:4] == ["Z_1", "Z_2", "Z_3", "Z_4"]
    assert order[4:] == ["ZZ_1,2", "ZZ_2,3", "ZZ_3,4"]


def test_observable_terms_match_expected_pauli_strings() -> None:
    terms = build_observable_terms(3)
    assert terms == ["Z0", "Z1", "Z2", "Z0 Z1", "Z1 Z2"]


def test_stack_embedding_snapshots_returns_time_as_second_axis() -> None:
    stacked = stack_embedding_snapshots([
        np.array([1.0, 2.0, 3.0]),
        np.array([4.0, 5.0, 6.0]),
    ])
    assert stacked.shape == (3, 2)
    assert np.allclose(stacked[:, 0], [1.0, 2.0, 3.0])
    assert np.allclose(stacked[:, 1], [4.0, 5.0, 6.0])
