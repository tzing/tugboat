---
name: argo-schema-models
description: Use when adding, updating, or comparing tugboat Pydantic schemas against Argo Workflows' official field reference, including missing fields and nested data models.
---

# Argo schema models

Translate the requested Argo specification into the existing `tugboat/schemas/`
models. Keep module dependencies one-way and distinguish structural validation
from analyzer rules.

## 1. Read the source

- Open the user's official documentation URL. Otherwise start at the
  [Argo field reference](https://argo-workflows.readthedocs.io/en/latest/fields/).
  Honor a requested release; `latest` can change independently of this repository.
- Read the parent field's type and description, then follow its nested type link.
  Capture field names, types, optionality, defaults, and semantic constraints.
  If requiredness or a displayed map type is ambiguous, consult the linked
  official API source or schema for the same version; do not infer it from an
  example alone. Report unresolved ambiguity.
- Search the reference for other consumers of the same type. Distinguish direct
  fields from resources that reuse a parent model. Read relevant official YAML
  examples, including overrides when applicable.

## 2. Locate the model

Search `tugboat/schemas/` for the field, type, and existing imports before adding
a class. Check related analyzers in `tugboat/analyzers/` for semantic checks.
Compare reused nested models with the official type too: existing restrictions
or missing fields can limit compatibility. Report those gaps rather than assuming
that an existing class fully implements the specification.

Place a shared type in the existing domain module that its consumers can already
depend on. Sharing alone is not a reason to move it into `basic.py`. For example,
`workflow.py` imports `template`, so `PodResourceClaim` lives in
`tugboat/schemas/template/__init__.py`; both `Template` and `WorkflowSpec` use it.
Check the actual import graph before applying this pattern to another type.

Update the relevant direct consumers within the requested scope. Inherited uses,
such as `WorkflowTemplate.spec` and `CronWorkflow.spec.workflowSpec`, should reuse
the model. Similar names do not imply identical types: container
`resources.claims` uses `ResourceClaim`, not `PodResourceClaim`.

## 3. Map the fields

| Official type | Project representation |
| --- | --- |
| `string`, `integer`, `boolean` | `str`, `int`, `bool` |
| Named object | Existing or new Pydantic model |
| Array of T | `Array[T]` from `schemas.basic` (tuple) |
| Map of K to V | `Dict[K, V]` from `schemas.basic` (frozen dictionary) |
| Optional field | Usually `T \| None = None`, following the parent model |

- Preserve manifest field spelling. Use `Field(alias=...)` for differing Python
  names, following nearby examples such as `artifactGc` / `artifactGC`.
- Use the module's `_BaseModel`, or `ConfigDict(extra="forbid", frozen=True)`.
  Keep typed fields ordered with their peers and separate from `Any` placeholders.
- For a requested nested data model, define its documented fields and connect
  callers with `Array[Model]` or `Model`; `Any` does not implement that model.
- Preserve omission instead of copying controller runtime defaults into Python.
  Determine required fields using the specification and the parent's existing
  validation contract. Many parent fields are optional so analyzers can diagnose
  incomplete manifests.
- Keep cross-field rules, naming rules, and runtime behavior distinct from type
  validation. If adding an analyzer is requested, follow `docs/plugin/rules.rst`.
  State any documented constraints not enforced by the model.
- Add a reStructuredText docstring linking the exact official type anchor.
  Update the module's `DOCUTILSCONFIG` exports for Sphinx discovery; add an API
  documentation section only if introducing a new module requires it.
- Avoid Sphinx naming collisions across combined autodoc content. For external
  Argo links, prefer anonymous inline links such as
  ```rst
  `PodResourceClaim <https://argo-workflows.readthedocs.io/en/latest/fields/#podresourceclaim>`__
  ```
  If using named targets, give them unique, descriptive names rather than bare
  class names. For internal references, use the appropriate Python role and
  fully qualified target, for example:
  ```rst
  :py:class:`~tugboat.schemas.template.PodResourceClaim`
  :py:attr:`~tugboat.schemas.workflow.WorkflowSpec.resourceClaims`
  :py:data:`~tugboat.schemas.basic.Array`
  ```
  The `~` shortens display text without weakening target resolution. Document a
  shared object at its owning module and link to it from consumers rather than
  registering duplicate object descriptions. Check the Sphinx build for duplicate
  targets, duplicate object descriptions, and ambiguous or unresolved references
  after changing docstrings or API documentation.

## 4. Verify and report

Use `tests/test_schemas.py` and relevant analyzer tests. For new validation,
exercise valid nested input and meaningful rejected input through the consuming
models. Check omission, serialization, and hashability where affected.

Parse relevant official examples from
`tests/fixtures/argo-workflows/examples/` when present. The schema integration
test is `tests/test_schemas.py::test_with_argo_examples`; its fixture skips when
the examples directory is absent, which is not evidence of compatibility.

Run appropriate checks using `poetry run pytest` (or the existing `.venv`
interpreter). Report the commands, results, and remaining failures accurately;
do not hide failing examples or expand the change to unrelated missing fields.
Summarize the source version/URL, affected models, and validation limits.
