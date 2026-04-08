# Task Breakdown: Python MindQuantum Backend with VQE and Exact-State Ground-State Paths

## 1. Document Control
- **Project**: qrc-phase
- **Task Stage**: Atomic Task Breakdown
- **Date**: 2026-04-08
- **Status**: Draft for review
- **Upstream Requirements**: `requirements.md:1-369`
- **Upstream Design**: `desing.md:1-752`

## 2. Purpose
This document converts the approved requirements and technical design into an executable, spec-driven implementation backlog.

The goal of this task list is to ensure the implementation proceeds in a controlled order and that each task is:
- small enough to execute and verify independently,
- explicitly scoped,
- traceable back to requirements and design,
- suitable for staged review.

This task list covers only the first delivered version defined in:
- `requirements.md:48-58`
- `desing.md:119-200`

That means the implementation target remains:
- **Python-only**,
- **eSSH-only in v1**,
- **MindQuantum for circuit evolution**,
- **two ground-state solver paths**: `vqe` and `exact_state`,
- **small-system bounded execution**.

## 3. Execution Rules
1. Implement tasks in the listed dependency order unless a later task is explicitly marked independent.
2. Do not start integration tasks before the relevant unit tasks pass.
3. Do not add Julia code for the new backend.
4. Do not silently relax the qubit-count guardrail.
5. Do not merge `vqe` and `exact_state` into one opaque solver path; solver identity must remain explicit in runtime metadata.
6. Every task that changes numerical behavior must include a verification step.
7. Every artifact schema decision must follow `desing.md:183-192` and `desing.md:515-539`.

## 4. Milestones
- **M1**: Python backend skeleton and config validation complete.
- **M2**: eSSH Hamiltonian builder complete.
- **M3**: `exact_state` solver path complete.
- **M4**: `vqe` solver path complete.
- **M5**: MindQuantum repeated-circuit evolution and observable extraction complete.
- **M6**: Output serialization and CLI entrypoint complete.
- **M7**: Validation, comparison, and failure-mode checks complete.

## 5. Atomic Task List

### Phase A. Repository and runtime scaffolding

#### T001. Create Python backend package skeleton
- **Objective**: Create the physical Python package layout defined in `desing.md:95-115`.
- **Inputs**:
  - `desing.md:95-115`
- **Actions**:
  1. Create `py_backend/` package.
  2. Create `py_backend/solvers/` subpackage.
  3. Add required `__init__.py` files.
  4. Create empty module files matching the approved design.
  5. Create `scripts/run_py_essh.py` entry script placeholder.
- **Outputs**:
  - package skeleton exists in the repository.
- **Depends on**: none.
- **Acceptance criteria**:
  - File layout matches `desing.md:95-115`.
  - Python can import `py_backend` without syntax errors.

#### T002. Declare Python dependencies for the new backend
- **Objective**: Add or update the Python dependency declaration so the new backend’s required libraries are explicit.
- **Inputs**:
  - `requirements.md:86-91`
  - `requirements.md:314-315`
  - `desing.md:139-145`
  - `desing.md:368-374`
  - `desing.md:408-421`
- **Actions**:
  1. Identify the repository’s existing Python dependency declaration mechanism.
  2. Add MindQuantum.
  3. Add NumPy.
  4. Add SciPy.
  5. Add any serialization helper dependency only if truly needed.
  6. Keep dependency scope minimal.
- **Outputs**:
  - updated dependency manifest.
- **Depends on**: T001.
- **Acceptance criteria**:
  - A fresh Python environment can install all required packages.
  - Dependency declaration clearly supports both `vqe` and `exact_state` paths.

#### T003. Add backend import smoke test
- **Objective**: Prove the repository can import the new Python backend and MindQuantum runtime.
- **Inputs**:
  - `requirements.md:314-315`
- **Actions**:
  1. Add a minimal automated smoke test or script.
  2. Import `py_backend`.
  3. Import MindQuantum.
  4. Fail clearly if import or version resolution fails.
- **Outputs**:
  - smoke test for installation validation.
- **Depends on**: T001, T002.
- **Acceptance criteria**:
  - The smoke test passes in a configured environment.
  - Failure output is actionable when dependencies are missing.

### Phase B. Typed configuration and runtime guardrails

#### T004. Implement typed config objects in `py_backend/config.py`
- **Objective**: Implement the configuration model described in `desing.md:238-299`.
- **Inputs**:
  - `requirements.md:280-310`
  - `desing.md:238-299`
- **Actions**:
  1. Define typed config structures for Hamiltonian, solver, circuit, runtime, and output sections.
  2. Represent solver-specific sub-configurations for `vqe` and `exact_state`.
  3. Provide config loading from CLI arguments and/or structured input.
  4. Normalize defaults.
- **Outputs**:
  - fully implemented config model.
- **Depends on**: T001.
- **Acceptance criteria**:
  - Config objects can represent every required input from `requirements.md:280-289`.
  - Invalid or incomplete config is rejected before execution.

#### T005. Implement qubit-count and feasibility guardrails
- **Objective**: Enforce the small-system limit before any expensive computation starts.
- **Inputs**:
  - `requirements.md:71-78`
  - `requirements.md:223-230`
  - `desing.md:126-138`
- **Actions**:
  1. Enforce `N <= max_qubits` at validation time.
  2. Reject unsupported dense diagonalization requests when problem size exceeds policy.
  3. Reject unsupported solver/method combinations.
  4. Emit clear error messages.
- **Outputs**:
  - validation logic for system-size feasibility.
- **Depends on**: T004.
- **Acceptance criteria**:
  - `N > 20` fails before solver construction.
  - infeasible dense exact diagonalization is rejected clearly.
  - unsupported solver type fails explicitly.

#### T006. Implement deterministic circuit-parameter resolution
- **Objective**: Resolve circuit parameters into explicit angle arrays before execution.
- **Inputs**:
  - `requirements.md:192-194`
  - `desing.md:171-181`
  - `desing.md:595-620`
- **Actions**:
  1. Support explicit input arrays.
  2. Support seeded generation from a rule-based configuration.
  3. Validate output array lengths against `N` and nearest-neighbor bond count.
  4. Return fully materialized `rx_angles`, `rz_angles`, `rzz_angles`.
- **Outputs**:
  - deterministic angle-resolution helper.
- **Depends on**: T004.
- **Acceptance criteria**:
  - identical seed and generation rule produce identical arrays.
  - angle-length mismatches fail before runtime.

### Phase C. Hamiltonian construction

#### T007. Implement eSSH Hamiltonian builder for matrix and MindQuantum forms
- **Objective**: Translate the repository’s eSSH Hamiltonian into Python representations usable by both solver families.
- **Inputs**:
  - `requirements.md:145-154`
  - `desing.md:300-326`
  - `hamiltonian.jl:123-141`
- **Actions**:
  1. Reproduce the eSSH bond pattern with alternating `J1` / `J2`.
  2. Add `XX`, `YY`, and `delta * ZZ` terms with matching coefficients.
  3. Add the `0.01 * Z_1` penalty term.
  4. Build a MindQuantum-compatible Hamiltonian representation.
  5. Build sparse-matrix representation.
  6. Support dense materialization lazily.
- **Outputs**:
  - `HamiltonianBundle` implementation.
- **Depends on**: T004, T005.
- **Acceptance criteria**:
  - coefficient pattern matches `hamiltonian.jl:123-141`.
  - both `mq_hamiltonian` and sparse-matrix forms are available.
  - open-boundary behavior matches the approved v1 scope.

#### T008. Add Hamiltonian unit tests against expected term structure
- **Objective**: Verify the Python eSSH builder encodes the intended operator pattern.
- **Inputs**:
  - `desing.md:310-326`
  - `desing.md:624-630`
- **Actions**:
  1. Add tests for small `N` values.
  2. Check alternating bond coefficients.
  3. Check presence of `XX`, `YY`, `ZZ`, and penalty terms.
  4. Check matrix dimensions and Hermiticity.
- **Outputs**:
  - Hamiltonian builder tests.
- **Depends on**: T007.
- **Acceptance criteria**:
  - tests pass for representative small-system cases.
  - any coefficient mismatch is caught automatically.

### Phase D. Shared solver contract

#### T009. Implement `PreparedState` contract and solver base interface
- **Objective**: Create the common abstraction used by both ground-state solvers.
- **Inputs**:
  - `desing.md:327-351`
- **Actions**:
  1. Define the `PreparedState` data structure.
  2. Define the base solver interface.
  3. Implement shared normalization checks.
  4. Implement shared metadata fields.
- **Outputs**:
  - solver base module and shared state contract.
- **Depends on**: T004, T007.
- **Acceptance criteria**:
  - both future solver paths can return the same normalized contract.
  - statevector shape and dtype checks are enforced.

### Phase E. Exact-state solver path

#### T010. Implement dense exact diagonalization path in `py_backend/solvers/exact_state.py`
- **Objective**: Support exact ground-state extraction with dense Hermitian diagonalization for very small systems.
- **Inputs**:
  - `requirements.md:165-172`
  - `desing.md:401-407`
  - `desing.md:430-434`
- **Actions**:
  1. Materialize dense Hamiltonian matrix when allowed.
  2. Compute the lowest eigenpair.
  3. Normalize the eigenvector.
  4. Package the result into `PreparedState`.
- **Outputs**:
  - `dense_eigh` path.
- **Depends on**: T007, T009.
- **Acceptance criteria**:
  - returns energy and statevector.
  - returns `solver_method = dense_eigh`.
  - fails clearly if dense path is requested beyond policy.

#### T011. Implement sparse Krylov-style eigensolver path in `py_backend/solvers/exact_state.py`
- **Objective**: Support ground-state extraction using a sparse Hermitian eigensolver for larger bounded systems.
- **Inputs**:
  - `requirements.md:165-172`
  - `desing.md:408-418`
  - `desing.md:435-447`
- **Actions**:
  1. Keep the Hamiltonian in sparse form.
  2. Request the lowest algebraic eigenpair.
  3. Normalize the returned eigenvector.
  4. Record convergence-related metadata.
- **Outputs**:
  - `sparse_eigsh` path.
- **Depends on**: T007, T009.
- **Acceptance criteria**:
  - returns energy and statevector.
  - returns `solver_method = sparse_eigsh`.
  - records solver summary fields when available.

#### T012. Implement `auto` dispatch policy for exact-state solving
- **Objective**: Select dense or sparse method according to problem size and policy.
- **Inputs**:
  - `desing.md:415-418`
  - `desing.md:693-697`
- **Actions**:
  1. Read `dense_qubit_threshold` from config.
  2. Dispatch to `dense_eigh` for sufficiently small systems.
  3. Dispatch to `sparse_eigsh` otherwise.
  4. Record the selected method explicitly in metadata.
- **Outputs**:
  - `auto` selection path.
- **Depends on**: T010, T011.
- **Acceptance criteria**:
  - chosen method is explicit in result metadata.
  - dispatch behavior is deterministic.

#### T013. Add exact-state integration test
- **Objective**: Verify the exact-state path can produce a statevector suitable for downstream circuit simulation.
- **Inputs**:
  - `requirements.md:325-331`
  - `desing.md:639-645`
- **Actions**:
  1. Build a small eSSH Hamiltonian.
  2. Run `exact_state` with one supported method.
  3. Assert normalized statevector output.
  4. Assert solver metadata completeness.
- **Outputs**:
  - exact-state integration test.
- **Depends on**: T010, T011, T012.
- **Acceptance criteria**:
  - test passes end to end for at least one small system.

### Phase F. VQE solver path

#### T014. Implement VQE ansatz builder
- **Objective**: Build the approved v1 ansatz structure for spin-chain ground-state preparation.
- **Inputs**:
  - `requirements.md:156-163`
  - `desing.md:356-366`
- **Actions**:
  1. Implement Neel-state initialization option.
  2. Implement parameterized single-qubit rotation layers.
  3. Implement alternating nearest-neighbor entangling blocks.
  4. Expose ansatz depth and parameter count.
- **Outputs**:
  - reusable VQE ansatz builder.
- **Depends on**: T009.
- **Acceptance criteria**:
  - ansatz can be instantiated for arbitrary supported `N` and depth.
  - parameter ordering is deterministic and documented in code.

#### T015. Implement VQE optimization loop in `py_backend/solvers/vqe.py`
- **Objective**: Run variational optimization and return a `PreparedState`.
- **Inputs**:
  - `desing.md:368-382`
  - `desing.md:384-390`
- **Actions**:
  1. Create MindQuantum simulator.
  2. Build expectation-with-gradient closure against the eSSH Hamiltonian.
  3. Run SciPy L-BFGS-B.
  4. Extract final energy, parameters, and statevector.
  5. Package VQE summary metadata.
- **Outputs**:
  - working `vqe` solver path.
- **Depends on**: T007, T009, T014.
- **Acceptance criteria**:
  - returns energy and statevector.
  - records optimizer name, iteration count, and convergence flag.
  - fails explicitly on optimizer failure.

#### T016. Add VQE convergence and reproducibility tests
- **Objective**: Validate VQE on a small problem and ensure seeding behavior is controlled.
- **Inputs**:
  - `requirements.md:83-84`
  - `requirements.md:317-323`
  - `desing.md:631-637`
- **Actions**:
  1. Run VQE on a small eSSH instance.
  2. Verify the output statevector is normalized.
  3. Verify the result includes convergence metadata.
  4. Verify seeded initialization is reproducible under fixed settings.
- **Outputs**:
  - VQE integration and reproducibility tests.
- **Depends on**: T015.
- **Acceptance criteria**:
  - test passes on a representative small system.
  - repeated runs under the same seed produce consistent initialization and deterministic outputs within tolerance.

### Phase G. Ground-state-to-circuit handoff and repeated evolution

#### T017. Implement direct statevector injection into MindQuantum simulator
- **Objective**: Realize the required solver-output-to-circuit handoff without ITensor or HDF5 mediation.
- **Inputs**:
  - `requirements.md:174-180`
  - `desing.md:147-153`
  - `desing.md:479-486`
  - `desing.md:573-583`
- **Actions**:
  1. Create a fresh MindQuantum simulator from `PreparedState.num_qubits`.
  2. Load the normalized statevector into the simulator.
  3. Validate shape, dtype, and normalization before injection.
  4. Reject invalid statevectors clearly.
- **Outputs**:
  - shared state-injection helper.
- **Depends on**: T009, T013, T015.
- **Acceptance criteria**:
  - both `vqe` and `exact_state` outputs can be injected successfully.
  - no intermediate ITensor serialization is required.

#### T018. Implement repeated circuit builder in `py_backend/repeated_circuit.py`
- **Objective**: Build the approved per-cycle circuit structure.
- **Inputs**:
  - `requirements.md:182-194`
  - `desing.md:451-457`
- **Actions**:
  1. Build an `Rx` layer over all qubits.
  2. Build nearest-neighbor `Rzz` layer.
  3. Build an `Rz` layer over all qubits.
  4. Support repetition for depth `d`.
- **Outputs**:
  - circuit-construction helper.
- **Depends on**: T006.
- **Acceptance criteria**:
  - generated circuit structure matches the approved notebook-derived order.
  - angle application count matches qubit and bond counts.

#### T019. Implement trajectory runner for repeated-circuit evolution
- **Objective**: Execute the full circuit trajectory from a prepared ground state.
- **Inputs**:
  - `desing.md:459-477`
  - `desing.md:479-486`
- **Actions**:
  1. Inject initial statevector.
  2. Measure observables at `t = 0`.
  3. Apply one circuit cycle.
  4. Measure observables after each cycle.
  5. Assemble full trajectory result.
- **Outputs**:
  - `TrajectoryResult` implementation.
- **Depends on**: T017, T018, T021.
- **Acceptance criteria**:
  - output contains exactly `d + 1` time slices.
  - stored metadata preserves solver identity and circuit parameters.

### Phase H. Observable extraction

#### T020. Implement canonical observable-order builder
- **Objective**: Fix a stable and explicit observable ordering.
- **Inputs**:
  - `requirements.md:196-205`
  - `desing.md:155-169`
  - `desing.md:491-508`
- **Actions**:
  1. Generate labels for `Z_1 .. Z_N`.
  2. Generate labels for `ZZ_1,2 .. ZZ_{N-1,N}`.
  3. Return the final stable ordering list.
- **Outputs**:
  - observable-order helper.
- **Depends on**: T001.
- **Acceptance criteria**:
  - returned order has length `2N - 1`.
  - order matches the design contract exactly.

#### T021. Implement embedding snapshot measurement
- **Objective**: Measure the required observables directly from the simulator state.
- **Inputs**:
  - `requirements.md:196-205`
  - `desing.md:491-510`
- **Actions**:
  1. Measure all `Z_i` expectations.
  2. Measure all nearest-neighbor `Z_i Z_{i+1}` expectations.
  3. Concatenate them in canonical order.
  4. Return a vector of length `2N - 1`.
- **Outputs**:
  - snapshot measurement helper.
- **Depends on**: T020.
- **Acceptance criteria**:
  - snapshot length equals `2N - 1`.
  - same observable order is used at every time slice.

#### T022. Add observable extraction tests
- **Objective**: Verify observable ordering and output shape.
- **Inputs**:
  - `desing.md:624-627`
- **Actions**:
  1. Test observable-order length.
  2. Test measurement vector length.
  3. Test embedding matrix shape after a short trajectory.
- **Outputs**:
  - observable tests.
- **Depends on**: T020, T021, T019.
- **Acceptance criteria**:
  - output shape is `(2N - 1, d + 1)`.

### Phase I. Persistence and CLI

#### T023. Implement NPZ + JSON serialization in `py_backend/io.py`
- **Objective**: Persist results using the approved artifact schema.
- **Inputs**:
  - `requirements.md:207-213`
  - `requirements.md:299-310`
  - `desing.md:183-192`
  - `desing.md:515-539`
- **Actions**:
  1. Save embedding matrix into `result.npz`.
  2. Save explicit circuit-angle arrays into `result.npz`.
  3. Optionally save final statevector.
  4. Save structured run metadata into `metadata.json`.
  5. Ensure schema version is written.
- **Outputs**:
  - artifact writer implementation.
- **Depends on**: T019.
- **Acceptance criteria**:
  - output files exist after a successful run.
  - metadata contains solver type, solver method, Hamiltonian parameters, seed, and circuit summary.

#### T024. Implement canonical output-path builder
- **Objective**: Create stable output directories that encode the physical run point and solver identity.
- **Inputs**:
  - `desing.md:533-539`
- **Actions**:
  1. Build path fragments from Hamiltonian, solver, depth, and seed.
  2. Create directories safely.
  3. Support explicit user override of output directory.
- **Outputs**:
  - output-path helper.
- **Depends on**: T023.
- **Acceptance criteria**:
  - generated paths are deterministic.
  - solver type and method are reflected in the path or metadata.

#### T025. Implement CLI entrypoint in `scripts/run_py_essh.py`
- **Objective**: Provide a top-level Python-only execution path for the new workflow.
- **Inputs**:
  - `requirements.md:121-127`
  - `requirements.md:215-221`
  - `desing.md:558-569`
- **Actions**:
  1. Parse command-line arguments.
  2. Load and validate config.
  3. Build Hamiltonian.
  4. Dispatch to `vqe` or `exact_state`.
  5. Run repeated-circuit trajectory.
  6. Save outputs.
- **Outputs**:
  - runnable CLI script.
- **Depends on**: T004, T006, T007, T012, T015, T019, T023.
- **Acceptance criteria**:
  - user can run the full workflow from Python without Julia.
  - unsupported inputs fail before expensive execution.

### Phase J. Batch execution and comparison tooling

#### T026. Implement batch execution over multiple eSSH parameter points
- **Objective**: Support repository-style parameter sweeps.
- **Inputs**:
  - `requirements.md:215-221`
- **Actions**:
  1. Accept multiple parameter points or a sweep configuration.
  2. Run points sequentially.
  3. Isolate outputs by point.
  4. Record failures per point without corrupting neighboring outputs.
- **Outputs**:
  - batch execution mode.
- **Depends on**: T025.
- **Acceptance criteria**:
  - each parameter point produces an isolated artifact directory.
  - one failed point does not erase successful neighboring results.

#### T027. Implement ITensor comparison helper in `py_backend/compare_itensor.py`
- **Objective**: Support small-system validation against the existing backend.
- **Inputs**:
  - `requirements.md:232-238`
  - `desing.md:541-557`
- **Actions**:
  1. Load Python-backend outputs.
  2. Load or ingest ITensor-reference observables.
  3. Compare energies when available.
  4. Compare `t = 0` and full-trajectory embedding values.
  5. Produce a structured comparison summary.
- **Outputs**:
  - comparison helper.
- **Depends on**: T023.
- **Acceptance criteria**:
  - comparison outputs quantitative error metrics.
  - comparison is performed at observable level, not raw state-container level.

#### T028. Add cross-solver comparison test (`vqe` vs `exact_state`)
- **Objective**: Validate the two ground-state preparation modes against each other on a small reference point.
- **Inputs**:
  - `desing.md:660-664`
- **Actions**:
  1. Run `exact_state` on a small eSSH instance.
  2. Run `vqe` on the same instance.
  3. Compare energies.
  4. Compare `t = 0` observables.
  5. Compare trajectory embeddings under identical circuit parameters.
- **Outputs**:
  - cross-solver validation test.
- **Depends on**: T013, T016, T019.
- **Acceptance criteria**:
  - solver-to-solver differences are reported quantitatively.
  - large discrepancies fail the validation threshold.

### Phase K. Failure-mode validation and hardening

#### T029. Add explicit failure-mode tests
- **Objective**: Verify required error paths from the spec.
- **Inputs**:
  - `requirements.md:336-342`
  - `desing.md:666-677`
- **Actions**:
  1. Test unsupported qubit count.
  2. Test invalid Hamiltonian parameters.
  3. Test missing dependency handling where feasible.
  4. Test VQE optimizer failure surfacing.
  5. Test exact-state solver failure surfacing.
- **Outputs**:
  - failure-mode validation suite.
- **Depends on**: T005, T015, T012, T025.
- **Acceptance criteria**:
  - all major failure classes are surfaced explicitly.
  - no silent fallback between solver types occurs.

#### T030. Run end-to-end validation matrix for the approved v1 scope
- **Objective**: Execute the minimum validation set needed for delivery confidence.
- **Inputs**:
  - `requirements.md:317-342`
  - `desing.md:622-665`
- **Actions**:
  1. Run import smoke validation.
  2. Run one VQE-path end-to-end case.
  3. Run one exact-state-path end-to-end case.
  4. Run one small-system comparison case against ITensor.
  5. Run one cross-solver comparison case.
  6. Archive outputs and test results.
- **Outputs**:
  - validated v1 implementation evidence.
- **Depends on**: T003, T013, T016, T027, T028, T029.
- **Acceptance criteria**:
  - all required validation categories from the approved requirements are executed successfully.

## 6. Dependency Graph Summary
The recommended execution order is:

1. `T001 -> T002 -> T003`
2. `T004 -> T005 -> T006`
3. `T007 -> T008`
4. `T009`
5. `T010 + T011 -> T012 -> T013`
6. `T014 -> T015 -> T016`
7. `T020 -> T021`
8. `T017 + T018 + T021 -> T019 -> T022`
9. `T023 -> T024 -> T025 -> T026`
10. `T027 + T028 + T029 -> T030`

## 7. Parallelization Guidance
The following tasks may be executed in parallel once their dependencies are satisfied:
- `T010` and `T011`
- `T014` and `T020`
- `T027` and `T029` after core runtime is stable

The following tasks should **not** be parallelized initially because they define contracts used elsewhere:
- `T004`
- `T007`
- `T009`
- `T019`
- `T023`

## 8. Definition of Done
The first-version feature is done only when all of the following are true:
1. A Python-only command path can run the eSSH workflow end to end.
2. The user can explicitly choose `vqe` or `exact_state`.
3. The selected solver returns a ground-state statevector.
4. That statevector is injected directly into MindQuantum for subsequent repeated-circuit evolution.
5. The embedding matrix has canonical shape `(2N - 1, d + 1)`.
6. Outputs are written as `result.npz` plus `metadata.json`.
7. Small-system guardrails are enforced.
8. At least one VQE validation case passes.
9. At least one exact-state validation case passes.
10. At least one small-system comparison case is runnable.
11. Failure-mode validation is present for the required error classes.

## 9. Deferred Items
The following are intentionally deferred beyond v1 unless separately approved:
- additional Hamiltonian families beyond eSSH,
- GPU-specific optimization,
- legacy CSV compatibility exporters,
- Julia wrappers for the new Python backend,
- large-system tensor-network replacement attempts,
- exact reproduction of the missing `dtc_circuit.jl` API.

## 10. Review Checklist
Before implementation starts, review the following decisions against the task list:
1. Is the package layout in `T001` acceptable?
2. Is `exact_state` correctly interpreted as Python dense/sparse eigensolvers rather than Julia KrylovKit?
3. Is the output contract `result.npz + metadata.json` acceptable?
4. Is the proposed validation burden sufficient for both solver paths?
5. Is the v1 scope still limited to eSSH and small-system runs?

## 11. Final Task Summary
This task plan turns the approved spec and design into **30 executable atomic tasks** covering:
- backend scaffolding,
- dependency declaration,
- typed config and runtime guardrails,
- eSSH Hamiltonian construction,
- `exact_state` solver implementation,
- `vqe` solver implementation,
- statevector handoff into MindQuantum,
- repeated circuit evolution,
- embedding extraction,
- output serialization,
- CLI and batch execution,
- backend comparison,
- and validation hardening.

Implementation should begin only after this task list is reviewed and approved.
