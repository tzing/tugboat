# Agent guidance

tugboat is an Argo Workflows manifest linter. Use the product name deliberately
and avoid unnecessary repetition.

## Project

- Code: `tugboat/`; built-in analyzers: `tugboat/analyzers/`.
- Tests: `tests/`, using pytest.
- Documentation: `docs/`, using Sphinx and reStructuredText.
- Tools: Python 3.12+, Poetry, black formatting, and ruff linting.

## Workflow

- For Argo data models, use the [argo-schema-models skill](.agents/skills/argo-schema-models/SKILL.md).
- For new analysis rules, follow `docs/plugin/rules.rst`.
- Keep `AGENTS.md` current when tooling or conventions change. Verify against
  `pyproject.toml`, CI, and project sources; flag unresolved ambiguity.
- Group related edits and prepare them for review. Maintainers or tooling can
  handle commits; formatting and linting are optional for agents.
- Verify commands, paths, and versions. Write concise, actionable guidance with
  short headings and project-standard tool names.
