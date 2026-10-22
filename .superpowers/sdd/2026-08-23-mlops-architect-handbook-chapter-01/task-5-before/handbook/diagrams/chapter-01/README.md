# Chapter 1 Diagrams

## Purpose

This directory is the figure registry for the editable, text-based diagrams that support Chapter 1. The registry describes planned figures without claiming that diagram files or semantic reviews exist.

## Metadata contract

Each registry row and final diagram must provide these fields:

- Figure ID
- Filename
- Section
- Purpose
- Assumptions
- Legend
- Provenance
- Alt text
- Semantic reviewer
- Review status

Use `Original handbook synthesis` for a new diagram. An adapted diagram names its source key and describes the adaptation. The semantic reviewer verifies arrow direction, responsibility boundaries, labels, and the relationship between the diagram and the associated chapter prose.

## Planned figure registry

| Figure ID | Filename | Section | Purpose | Assumptions | Legend | Provenance | Alt text | Semantic reviewer | Review status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fig-01-ml-lifecycle | fig-01-ml-lifecycle.mmd | ML lifecycle and operational feedback loops | Show lifecycle stages and feedback boundaries. | Chapter assumptions pending research. | Pending diagram design. | Original handbook synthesis planned. | Pending diagram design. | Unassigned. | Planned |
| fig-02-architecture-planes | fig-02-architecture-planes.mmd | Architecture planes | Separate control, data, training, and serving responsibilities. | Chapter assumptions pending research. | Pending diagram design. | Original handbook synthesis planned. | Pending diagram design. | Unassigned. | Planned |
| fig-03-systems-of-record | fig-03-systems-of-record.mmd | System-of-record boundaries | Identify authoritative stores and ownership boundaries. | Chapter assumptions pending research. | Pending diagram design. | Original handbook synthesis planned. | Pending diagram design. | Unassigned. | Planned |
| fig-04-failure-propagation | fig-04-failure-propagation.mmd | Production failure case study | Trace a failure path, detection, containment, and recovery boundary. | Chapter assumptions pending research. | Pending diagram design. | Original handbook synthesis planned. | Pending diagram design. | Unassigned. | Planned |

The filenames are registry values, not links, until Task 6 creates the approved diagram files. The release validator then requires each approved filename to be registered once as a resolvable link.

## Review rules

- Keep figure IDs stable once chapter prose cites them.
- Keep component names consistent with the chapter and glossary.
- Record source-key attribution for adapted diagrams.
- Do not mark a figure beyond `Planned` until its required metadata and semantic review are complete.

## Changelog

### 2026-08-23

- Expanded the diagram scaffold into the binding metadata contract and registered four planned Chapter 1 figures.
