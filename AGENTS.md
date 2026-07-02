# Axiom Platform Agent Instructions

These instructions apply to every coding agent working in this repository.
The repository is the shared source of truth; chat history is not.

## Start-of-session protocol

Before changing anything:

1. Read `AGENTS.md`, `PROJECT_STATE.md`, and `HANDOFF.md`.
2. Inspect `git status`, recent commits, and any uncommitted diff.
3. Verify that the previous handoff matches the actual files.
4. Run the smallest safe baseline check relevant to the task.
5. State any assumption that would change workflow behavior or client output.

If documentation and code disagree, trust neither automatically. Verify the
behavior, then update the documentation in the same change.

## Canonical project boundary

The canonical code root is the directory containing this file and `axiom.py`.
Do not develop against an older copied folder. Only one agent should edit the
working branch at a time unless separate branches have been intentionally
created.

## Data and client-safety rules

- Treat everything under `assignments/` as confidential by default, even when
  a current assignment is a demo.
- `tests/fixtures/DEMO-001/` is the only approved source-controlled assignment
  fixture. Its identity and property data are conspicuously fictional.
- Never commit, publish, paste into chat, or use live assignment data as a
  distributable test fixture.
- Never modify a delivered assignment merely to test the platform. Work from
  `tests/fixtures/DEMO-001/` or a disposable copy outside `assignments/`.
- Never send an email, invoice, agreement, API request, or e-signature package
  without Derek's explicit instruction. Document generation is not permission
  to transmit it.
- Never place credentials in source-controlled files. Real Adobe Sign, Xero,
  Anthropic, or other credentials stay in ignored local configuration or an
  approved secret store.
- AI-generated narrative is a draft for appraiser review. Do not describe it as
  USPAP-compliant solely because a prompt requested compliant language.

## Workflow invariants

- `axiom.py engage` currently generates local documents; it does not send them.
- A document containing unresolved required placeholders is not deliverable.
- An assignment must not transition to `delivered` merely because a file was
  generated.
- Block placeholders must be either resolved by a registered pipeline handler
  or reported as blockers. They must not be silently treated as ready.
- Workbook formulas are read through cached Excel values. Validation must
  account for stale or missing cached results.
- Presentation variants such as lowercase text or words-formal values should be
  derived from canonical facts where practical, not entered independently.
- `schemas/field_registry.v1.json` is the field contract. Register and version a
  key before adding it to a workbook, JSON export, template, or block handler.
- Run `python axiom.py contract` after any workbook, template, or registry
  change.

## Git and handoff discipline

- Keep commits small and describe behavior, not the agent that made the change.
- Do not commit client assignments, credentials, databases, ingest staging
  files, generated dashboards, or Office lock files.
- Do not push or create a remote repository without Derek's explicit approval.
- Before handing off, either commit the coherent work or clearly list every
  uncommitted file and why it remains uncommitted.
- Update `HANDOFF.md` at every baton pass.
- Update `PROJECT_STATE.md` whenever architecture, verified capability,
  priority, or a known limitation changes.

## Definition of done

A workflow change is not complete until:

- failure behavior is defined;
- the safest relevant automated or dry-run checks pass;
- no live assignment was mutated by testing;
- user-facing documentation is consistent with the implementation; and
- `HANDOFF.md` names the exact next step, even if no work remains.
