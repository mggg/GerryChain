# Developer documentation

This directory contains engineering documentation that belongs in the repository but is not
published with the user documentation in `docs/`.

Folder descriptions:

- `ADRs/` for accepted architectural decision records (ADRs);
- `specifications/` for durable descriptions of the current system; and
- `design-blueprints/` for proposals and implementation plans that are still in progress.

Name ADRs with a sequential number and short description, such as
`0001-rust-core-layout.md`. Each ADR should record its status, context, decision, and
consequences. ADRs should be created following the implementation of a plan outlined in a design
blueprint, while still fresh in the mind of the implementer. Blueprints should be written with
natural stopping points (stages / milestones) that simplify the review process and which serve
as a natural stopping point for the implementer to write an ADR should the implementation be
approved.
