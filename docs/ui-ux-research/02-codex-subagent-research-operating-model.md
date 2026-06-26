# Codex Subagent Research Operating Model

## Purpose

This model defines how to use Codex subagents and multi-chat research threads to improve Hermes Company OS without turning research into scattered opinions.

The pattern is:

1. Central agent defines the research batch.
2. Focused Codex threads research one surface or workflow each.
3. Each thread writes one research package using the standard template.
4. Central integration merges packages and resolves conflicts.
5. Founder reviews and approves the integrated plan.
6. Implementation begins only after approval.

## Why This Exists

Hermes Company OS is intended to become a founder-led AI company. That requires many interfaces:

- decision inbox;
- Product Wizard;
- agent queues;
- review findings;
- live runs;
- memory;
- project execution;
- audit;
- launch.

Those surfaces are too broad for one generic UI pass. Parallel research lets each surface get focused attention while central integration prevents fragmentation.

## Roles

Central Integration Agent:

- owns the research batch;
- assigns research threads;
- checks every package for completeness;
- resolves conflicts;
- updates source docs;
- prepares founder approval summary.

UI/UX Research Thread:

- investigates one workflow;
- uses the research package template;
- avoids source edits unless explicitly assigned implementation later;
- names assumptions and founder decisions needed.

Implementation Agent:

- starts only after integrated research is approved;
- turns accepted recommendations into source changes;
- keeps tests and no-secret scans green.

QA Thread:

- reviews the implementation plan and final output;
- checks accessibility, state coverage, and regression risk.

## Research Batch Lifecycle

### 1. Batch Definition

The central agent creates a short batch brief:

- objective;
- surfaces in scope;
- out-of-scope areas;
- required package template;
- expected output paths;
- conflict-resolution rule;
- deadline or stopping condition;
- founder approval gate.

### 2. Thread Assignment

Each thread receives:

- exact research prompt;
- relevant docs to read;
- output package path;
- required sections;
- guardrails:
  - no credentials;
  - no live AppData writes;
  - no source implementation;
  - no broad unrelated repo exploration.

### 3. Package Production

Each thread writes one package with:

- findings;
- recommended screens;
- required states;
- risks;
- implementation notes;
- acceptance checklist.

The package is not accepted if it omits failure states, accessibility, or founder decisions.

### 4. Central Integration

The central agent:

- reads all packages;
- deduplicates recommendations;
- resolves conflicts using the roadmap and operating model;
- records unresolved founder questions;
- updates the roadmap or implementation plan;
- runs no-secret scans.

### 5. Founder Approval

Founder approves:

- the integrated UX direction;
- the first implementation slice;
- any changes to autonomy, escalation, or launch behavior.

### 6. Implementation Handoff

The handoff must include:

- source files likely affected;
- data model changes if needed;
- route and UI changes;
- tests to add;
- acceptance criteria;
- no-secret scan requirement.

## Conflict Resolution

Resolve conflicts in this order:

1. Founder explicit decisions.
2. Existing operating model.
3. Roadmap maturity sequence.
4. Safety and no-secret guardrails.
5. Testability and reversibility.
6. UI/UX Research Agent doctrine.

If conflict remains, stop and ask founder.

## Standard Research Threads

Initial threads:

- Founder Control Plane UX.
- Product Wizard UX.
- Agent Work Queue UX.
- Observability and Audit UX.
- Codex Project Execution UX.
- Accessibility and Responsive UX.
- Design System and Visual Polish.

## Done Criteria For A Research Batch

A research batch is done when:

- every assigned package exists;
- every package follows the template;
- no package contains secret-looking values;
- central integration summary exists;
- implementation plan has clear first slice;
- founder decisions are listed;
- founder has approved or rejected the batch.

## Testing And Verification

For documentation-only batches:

- run no-secret scan over new docs;
- run docs tests if available;
- verify all links and paths are consistent.

For implementation batches:

- run focused tests for touched routes and repositories;
- run UI route assertions for founder-visible states;
- run full test suite when schema, routes, or templates change;
- run no-secret scan over generated docs and artifacts.
