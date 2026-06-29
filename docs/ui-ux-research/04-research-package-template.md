# UI/UX Research Package Template

Copy this template for every focused UI/UX research thread.

Output path pattern:

`docs/ui-ux-research/packages/<topic>.md`

## Package Metadata

- Package title:
- Research thread:
- Owner:
- Date:
- Source docs reviewed:
- Current implementation areas inspected:
- Scope:
- Out of scope:

## Research Question

State the exact question this package answers.

## Target Workflow

Describe the founder, agent, or reviewer workflow being improved.

Include:

- entry point;
- primary job to be done;
- expected outcome;
- approval or review moment;
- exit state.

## User And Persona Assumptions

List assumptions about:

- founder behavior;
- agent behavior;
- reviewer behavior;
- frequency of use;
- urgency;
- information density tolerance.

Mark assumptions that need founder confirmation.

## Current-State Notes

Summarize what currently exists in the repo or dashboard.

Include:

- relevant routes or screens;
- relevant docs;
- existing state labels;
- known test coverage;
- gaps.

## Screens Needed

List each required screen or view.

For each screen:

- purpose;
- primary user;
- primary action;
- secondary actions;
- empty state;
- blocked state;
- failed state;
- success state.

## State Model

List the states the UI must represent.

For each state:

- label;
- meaning;
- owner;
- allowed actions;
- forbidden actions;
- evidence required.

## UX Risks And Anti-Patterns

List risks such as:

- confusing approval state;
- hidden blockers;
- overconfident generated text;
- unclear owner;
- missing failure handling;
- inaccessible interaction;
- too much visual decoration;
- premature execution.

## Accessibility And Responsive Notes

Include:

- keyboard behavior;
- labels and semantic structure;
- contrast and status color concerns;
- mobile layout concerns;
- long text handling;
- focus management;
- motion or animation constraints.

## Implementation Recommendations

Write recommendations that can become engineering tasks.

Each recommendation should include:

- behavior;
- affected surface;
- likely data needed;
- acceptance signal.

## Acceptance Checklist

Use checkboxes.

- [ ] Target workflow is clear.
- [ ] Required screens are listed.
- [ ] Required states are listed.
- [ ] Founder approval and revision paths are clear.
- [ ] Blocked and failed states are handled.
- [ ] Accessibility requirements are explicit.
- [ ] Recommendations can become tasks.
- [ ] Risks and anti-patterns are named.
- [ ] Founder decisions needed are explicit.
- [ ] No credentials or secret-looking values are included.

## Founder Decisions Needed

List exact founder questions.

Each question should include:

- decision;
- why it matters;
- default recommendation;
- impact if deferred.

## Implementation Handoff

Summarize the implementation-ready handoff:

- first slice;
- likely files or modules;
- tests to add;
- no-secret scan scope;
- founder approval gate.
