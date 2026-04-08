# Requirements: Python-Based MindQuantum Circuit Simulation with Multiple Ground-State Solvers

## 1. Document Control
- **Project**: qrc-phase
- **Spec Stage**: Requirements
- **Date**: 2026-04-08
- **Status**: Draft for review

## 2. Background
The current codebase uses an ITensor/ITensorMPS-based workflow to:
1. define lattice Hamiltonians,
2. compute ground states with DMRG,
3. persist the resulting many-body state as an MPS in HDF5,
4. load that ground state and apply a repeated quantum-circuit evolution stage,
5. extract embeddings from local observables.

This workflow is visible in the current repository through:
- Hamiltonian definitions in `hamiltonian.jl:4-196`
- DMRG-based ground-state generation in `getmps.jl:52-73` and `getessh.jl:23-69`
- ground-state loading plus circuit-stage entrypoints in `getemb.jl:14-30` and `getemb_clusterising.jl:16-31`
- notebook-level circuit and observable logic in `get_trivial_state_emb.ipynb:36-65`, `get_sb_state_emb.ipynb:36-64`, and `get_topo_state_emb.ipynb:83-112`

The requested new capability is to add a **Python-based** simulation path that keeps **MindQuantum** as the circuit-simulation runtime, while replacing the current “DMRG ground state -> MPS/tensor-network circuit simulation” stage with one of two small-system statevector-based paths:
1. **VQE ground state -> circuit simulation**
2. **exact / Krylov-style ground state statevector -> circuit simulation**

## 3. Problem Statement
The repository currently lacks a Python-only backend for this workflow and does not provide a complete checked-in implementation of the circuit helper referenced by the batch scripts (`dtc_circuit.jl` is referenced but absent in the repository) (`getemb.jl:7`, `getemb_clusterising.jl:8`).

As a result, the codebase cannot currently:
- compute the ground state with VQE in a Python-based MindQuantum workflow,
- compute the ground state with exact diagonalization or a Krylov-style eigensolver and obtain a statevector directly,
- represent either of those ground states in a MindQuantum-compatible simulator state,
- continue evolution from that ground state with the existing repeated circuit pattern,
- produce a backend-consistent embedding output for downstream analysis.

## 4. Goal
Add a new **Python-only** simulation workflow that:
1. builds a target Hamiltonian,
2. prepares a small-system ground state using a selectable solver,
3. uses that ground state statevector as the initial state of a subsequent quantum circuit,
4. applies the repeated circuit evolution in MindQuantum,
5. measures the same family of observables used by the current embedding workflow,
6. saves outputs in a reproducible format for downstream analysis and comparison.

## 5. Scope

### 5.1 In Scope
The first delivered version shall include:
- a new **Python-only backend** for this feature set;
- a new **MindQuantum-based circuit simulation backend**;
- a **VQE-based ground-state preparation flow**;
- an **exact-state ground-state preparation flow** based on either exact diagonalization or a Krylov-style eigensolver;
- support for the workflow “ground state -> repeated circuit -> embedding extraction”;
- support for at least the **eSSH-family workflow**, because it is the most complete active pipeline in the repository (`getessh.jl:11-69`, `getemb.jl:14-30`);
- the ability to run the new workflow independently from the existing ITensor/MPS scripts;
- reproducible parameterized runs with explicit control of Hamiltonian parameters, solver choice, circuit parameters, depth, and output location;
- output suitable for later numerical comparison with existing tensor-network results on small systems.

### 5.2 Out of Scope
The first delivered version shall **not** require:
- replacing or deleting the existing ITensor/ITensorMPS workflow;
- reproducing current large-system `N = 128` tensor-network runs with an exact statevector engine;
- adding any new Julia implementation for the new backend;
- migrating all historical notebooks and scripts to the new backend;
- changing downstream research conclusions or reprocessing all existing data artifacts;
- implementing a tensor-network simulator inside MindQuantum.

## 6. Key Assumptions and Constraints

### 6.1 Reality Constraint: System Size
The existing production scripts operate at sizes such as `N = 128` (`getessh.jl:11`, `getemb.jl:14`), while exact statevector workflows scale exponentially and therefore are not realistic drop-in replacements for generic 128-qubit simulation.

Therefore, the first Python-based version shall be specified as:
- a **small-system exact / near-exact validation backend**, or
- a backend whose supported qubit count is explicitly bounded and validated at runtime.

The implementation must reject unsupported system sizes with a clear error instead of silently attempting infeasible simulation.

### 6.2 Coexistence Constraint
The new Python workflow shall coexist with the current Julia + ITensor code and must not break existing scripts such as `getmps.jl`, `getessh.jl`, `getemb.jl`, or `getemb_clusterising.jl`.

### 6.3 Reproducibility Constraint
Any stochastic part of the new workflow, including VQE initialization and random circuit parameter generation if retained, shall support explicit seeding so that repeated runs are reproducible.

### 6.4 Dependency Constraint
The new functionality shall explicitly declare Python-side dependencies introduced by:
- MindQuantum,
- numerical eigensolver support,
- optimization support,
- output serialization support.

### 6.5 Host-Language Constraint
All newly added functionality for this feature set shall be implemented in **Python**, not Julia.

### 6.6 State-Handoff Constraint
The selected ground-state solver must produce a state representation that can be converted into or directly expressed as a **statevector** suitable for subsequent circuit evolution.

## 7. User Stories

### 7.1 Research User
As a researcher, I want to specify Hamiltonian parameters, choose a ground-state solver, continue with a repeated quantum circuit, and save the resulting embedding, so that I can study phase-related structure using a Python-only workflow.

### 7.2 Solver-Choice User
As a researcher, I want to choose between:
- a VQE-based approximate ground state,
- an exact-state ground state obtained from exact diagonalization or a Krylov-style eigensolver,
so that I can trade off approximation, runtime, and validation confidence on small systems.

### 7.3 Validation User
As a researcher, I want to run the same physical parameter point with both the existing tensor-network workflow and the new Python workflow on small systems, so that I can compare outputs and validate the new backend.

### 7.4 Batch User
As a researcher, I want to sweep over parameter ranges and save one result per parameter point, so that I can integrate the new backend into the repository’s existing data-generation workflow style.

### 7.5 Debugging User
As a developer, I want the new workflow to expose intermediate artifacts such as solver type, final energy, convergence information, and metadata, so that I can debug failures and compare behavior across backends.

## 8. Functional Requirements

### FR-1. Python-Only Entry Path
The codebase shall provide a Python-only way to invoke the new workflow without modifying the existing ITensor-based path.

**Acceptance criteria**
- A user can explicitly choose the Python workflow.
- The new workflow does not require new Julia implementation.
- Existing ITensor-based scripts continue to function unchanged unless the user opts into the new workflow.

### FR-2. Ground-State Solver Selection
The new workflow shall support explicit selection of the ground-state preparation method.

**Minimum first-version solver coverage**
- `vqe`
- `exact_state`

Where `exact_state` means a small-system solver that returns the ground-state statevector using either:
- dense exact diagonalization, or
- a Krylov-style sparse eigensolver.

**Acceptance criteria**
- A user can choose the solver type at runtime.
- The selected solver type is recorded in run metadata.
- Unsupported solver types are rejected clearly rather than partially executed.

### FR-3. Hamiltonian Support for Ground-State Solvers
The new workflow shall support constructing the target Hamiltonian for the selected ground-state solver from repository parameters.

**Minimum first-version coverage**
- eSSH parameterization: `J1`, `J2`, `delta`, `periodic`, `N`, reflecting the active repository pipeline (`hamiltonian.jl:123-141`, `getessh.jl:44-45`).

**Acceptance criteria**
- A user can provide the required eSSH Hamiltonian parameters.
- The workflow constructs the corresponding Hamiltonian needed by both `vqe` and `exact_state` solver paths.
- Unsupported Hamiltonian families are rejected clearly rather than partially executed.

### FR-4. VQE Ground-State Preparation
The `vqe` solver path shall compute an approximate ground state using a variational algorithm.

**Acceptance criteria**
- A run returns the final optimized energy.
- A run records convergence-related metadata sufficient for later inspection.
- A run exposes the final optimized quantum state in a form that can be used as the initial state for the next circuit stage.
- The workflow reports failure if VQE does not converge or cannot produce a valid state.

### FR-5. Exact-State Ground-State Preparation
The `exact_state` solver path shall compute a ground-state statevector using exact diagonalization or a Krylov-style eigensolver.

**Acceptance criteria**
- A run returns the ground-state energy.
- A run returns the ground-state statevector.
- A run records which exact-state method was used.
- The workflow reports failure if the eigensolver does not converge or cannot produce a valid state.

### FR-6. Ground-State-to-Circuit Handoff
The new workflow shall support using the output state of either solver path directly as the initial state for a subsequent repeated quantum circuit evolution.

**Acceptance criteria**
- The handoff does not require conversion through ITensor MPS/HDF5 as an intermediate mandatory step.
- The post-ground-state circuit stage begins from the computed ground state, not from `|0...0>` or another default basis state unless explicitly requested.
- The handoff contract works for both `vqe` and `exact_state` modes.

### FR-7. Circuit Structure Compatibility
The new workflow shall implement the repeated circuit structure currently implied by the repository notebooks:
- per-qubit `Rx` layer,
- nearest-neighbor `Rzz` layer,
- per-qubit `Rz` layer,
- repeated for `d` cycles.

This requirement is derived from `get_trivial_state_emb.ipynb:52-64`, `get_sb_state_emb.ipynb:52-64`, and `get_topo_state_emb.ipynb:99-111`.

**Acceptance criteria**
- A user can set the circuit depth `d`.
- A user can provide or reproduce the circuit parameters required by the repeated layer.
- The circuit is applied after the selected ground-state solver has prepared the initial state.

### FR-8. Observable Extraction
The new workflow shall extract the same observable family used in the current embedding notebooks:
- local `Z_i` expectation values,
- nearest-neighbor `Z_i Z_{i+1}` expectation values,
- recorded for the initial ground state and after each circuit cycle.

**Acceptance criteria**
- The output includes measurements at `t = 0`.
- The output includes measurements after each of the `d` circuit applications.
- The observable ordering is explicitly defined and stable across runs.

### FR-9. Embedding Output
The new workflow shall save an embedding artifact that is consumable by downstream analysis.

**Acceptance criteria**
- The output format is explicitly defined.
- Output files include enough metadata to identify the Hamiltonian point, solver type, circuit parameters, backend, and seed.
- The saved artifact is sufficient to reconstruct the measured embedding matrix dimensions and semantic meaning.

### FR-10. Batch Execution
The new workflow shall support scanning multiple parameter points in a repository-consistent batch style.

**Acceptance criteria**
- A user can run multiple eSSH parameter points in sequence.
- Each parameter point produces an isolated result artifact.
- A failed point is reported clearly and does not silently corrupt neighboring results.

### FR-11. Runtime Guardrails
The new workflow shall validate runtime feasibility before execution.

**Acceptance criteria**
- Unsupported qubit counts are rejected with a clear message.
- Invalid parameter combinations are rejected before starting expensive computation.
- Missing Python-side dependencies are detected and surfaced clearly.
- Solver-specific feasibility checks are enforced before runtime.

### FR-12. Comparison Readiness
The new workflow shall support backend comparison against the existing tensor-network path on small systems.

**Acceptance criteria**
- For a supported small system size, the output can be compared against the existing ITensor-based observable extraction workflow.
- Comparison runs use explicitly recorded parameters and seed values.
- Comparison metadata identifies which ground-state solver path produced the Python-side result.

## 9. Non-Functional Requirements

### NFR-1. Reproducibility
The workflow shall be reproducible given the same:
- code version,
- Hamiltonian parameters,
- selected solver type,
- solver configuration,
- circuit parameters,
- random seed.

### NFR-2. Transparency
The workflow shall emit enough metadata to diagnose:
- backend identity,
- Hamiltonian family,
- Hamiltonian parameters,
- selected ground-state solver,
- solver configuration,
- convergence summary or eigensolver summary,
- circuit depth,
- circuit parameters or their generation rule,
- output schema version.

### NFR-3. Failure Visibility
Failures shall be explicit and actionable. The workflow shall not silently fall back from one solver path to another.

### NFR-4. Maintainability
The new capability shall be implemented in a way that keeps:
- Hamiltonian specification,
- ground-state solver logic,
- circuit simulation,
- observable extraction,
- and orchestration
separated as much as possible.

### NFR-5. Backward Compatibility
Existing repository workflows shall remain runnable after the new functionality is added.

## 10. Data and Interface Requirements

### 10.1 Required Inputs
At minimum, the first version shall accept:
- Hamiltonian family identifier,
- `N`, `J1`, `J2`, `delta`, `periodic` for eSSH,
- solver type,
- solver configuration,
- circuit depth `d`,
- circuit parameters or a reproducible parameter-generation rule,
- random seed,
- output path.

### 10.2 Required Outputs
At minimum, each completed run shall produce:
- selected solver type,
- final ground-state energy,
- solver-specific result summary,
- measured embedding data,
- run metadata.

### 10.3 Output Metadata
Each output artifact shall include or be accompanied by metadata containing:
- circuit backend name = `mindquantum`,
- Hamiltonian family,
- full Hamiltonian parameters,
- system size,
- selected ground-state solver,
- solver configuration summary,
- circuit depth,
- circuit parameter summary,
- seed,
- timestamp or run identifier.

## 11. Validation Requirements

### VR-1. Installation Validation
There shall be a documented validation step proving that the Python runtime can import and execute MindQuantum.

### VR-2. VQE Path Validation
There shall be at least one automated or scripted validation scenario that executes:
1. Hamiltonian construction,
2. VQE ground-state preparation,
3. circuit continuation from the VQE state,
4. observable extraction,
5. output persistence.

### VR-3. Exact-State Path Validation
There shall be at least one automated or scripted validation scenario that executes:
1. Hamiltonian construction,
2. exact-state ground-state preparation,
3. circuit continuation from the exact ground-state statevector,
4. observable extraction,
5. output persistence.

### VR-4. Small-System Comparison Validation
There shall be at least one small-system reference case where the Python path is compared against the existing ITensor-based path for the same parameter point.

### VR-5. Failure-Mode Validation
There shall be validation for at least:
- unsupported qubit count,
- invalid Hamiltonian parameters,
- missing dependency or import failure,
- VQE non-convergence or optimizer failure,
- exact-state eigensolver failure or non-convergence.

## 12. Explicit Non-Goals
This requirements set does **not** require the first version to:
- reproduce tensor-network scalability,
- preserve ITensor HDF5 state-file compatibility as the primary state interchange format,
- support every Hamiltonian in `hamiltonian.jl` on day one,
- replace the missing `dtc_circuit.jl` with an identical implementation signature,
- expose a Julia API for the new feature.

## 13. Open Questions for Design Stage
The following items are intentionally deferred to the design document:
1. What the canonical Python package / module layout should be.
2. What output file format should be canonical for Python runs.
3. Whether circuit parameters are user-supplied, randomly generated, or both.
4. Which VQE ansatz and optimizer are selected for first delivery.
5. Whether the `exact_state` path defaults to dense exact diagonalization, a Krylov-style sparse eigensolver, or a size-dependent hybrid strategy.
6. Whether the first release includes only eSSH or also cluster-Ising support.
7. Whether comparison tooling is part of the initial implementation or only the core backend path.

## 14. Requirements Summary
The first version must deliver a **reviewable, reproducible, Python-only workflow** that:
- uses MindQuantum for circuit evolution,
- starts from either VQE ground-state preparation or exact-state ground-state preparation,
- continues with the repository’s repeated circuit pattern,
- measures the same embedding observables,
- saves comparison-ready outputs,
- and operates within explicitly bounded small-system limits rather than pretending to replace the existing 128-site MPS/tensor-network production workflow.
