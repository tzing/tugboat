Writing Rules
=============

This guide focuses on static-analysis rules that lint already validated workflows.
Tugboat validates manifests before plugins run, so hook arguments already match :mod:`tugboat.schemas`.

Rules sit at the core of any plugin: they run inside `pluggy`_ hooks and emit diagnoses when a manifest violates expectations.
Use the guidance below once your plugin skeleton from :doc:`index` is in place.

.. _pluggy: https://pluggy.readthedocs.io/en/stable/

Pick the Right Hook
-------------------

Rules attach to one of the workflow-scoped hooks defined in :py:mod:`tugboat.hookspecs`:

- :func:`~tugboat.hookspecs.workflow.analyze_workflow` inspects an entire `Workflow`_.
- :func:`~tugboat.hookspecs.workflow.analyze_workflow_template` runs before a `WorkflowTemplate`_ is instantiated.
- :func:`~tugboat.hookspecs.workflow.analyze_template` evaluates each template within a workflow or template.
- :func:`~tugboat.hookspecs.workflow.analyze_step` validates individual sequence steps with their parent template.

Pick the hook that matches the scope you care about.
:func:`~tugboat.hookspecs.workflow.analyze_workflow` and :func:`~tugboat.hookspecs.workflow.analyze_workflow_template` dispatch to the template and step hooks, so implementing :func:`~tugboat.hookspecs.workflow.analyze_template` or :func:`~tugboat.hookspecs.workflow.analyze_step` lets tugboat stitch the ``loc`` path while your rule concentrates on the specific violation.

.. _Workflow: https://argo-workflows.readthedocs.io/en/latest/workflow-concepts/#the-workflow
.. _WorkflowTemplate: https://argo-workflows.readthedocs.io/en/latest/workflow-templates/


Working with Schemas
--------------------

Because tugboat validates manifests before invoking plugins, hook arguments are trusted `Pydantic`_ models from :mod:`tugboat.schemas`.
Focus on linting logic—schema checks already passed.

The models you will use most often include:

- :py:class:`~tugboat.schemas.Workflow` / :py:class:`~tugboat.schemas.WorkflowTemplate`, whose ``spec`` objects surface templates, arguments, and entrypoint references.
- :py:class:`~tugboat.schemas.Template`, which exposes typed collections for steps, DAG tasks, inputs, and outputs.
- :py:class:`~tugboat.schemas.Step`, which mirrors fields such as ``name`` and ``arguments`` from the owning template.

Tugboat also stamps a ``kind`` attribute on workflow objects so a rule can differentiate Workflow and WorkflowTemplate contexts whenever behaviour differs.

.. _Pydantic: https://docs.pydantic.dev/latest/


Reporting Diagnoses
-------------------

Report each finding as a diagnosis — a plain Python :py:class:`dict` that matches :class:`~tugboat.types.Diagnosis`.
Tugboat collects these payloads to render CLI output and machine-readable reports.

Every diagnosis must include:

- :attr:`~tugboat.Diagnosis.code`: a unique identifier for the finding (reserve a namespace for your plugin, such as ``MYPLUGIN``).
- :attr:`~tugboat.Diagnosis.loc`: a tuple or list pointing to the manifest path (matching how users navigate their YAML).
- :attr:`~tugboat.Diagnosis.msg`: a concise, human-friendly description.

Optional keys such as :attr:`~tugboat.Diagnosis.type`, :attr:`~tugboat.Diagnosis.summary`, :attr:`~tugboat.Diagnosis.input`, and :attr:`~tugboat.Diagnosis.fix` enrich results when they add value.
Yield diagnoses directly or return an iterable; tugboat will flatten the results.

Example diagnosis payloads:

.. tab-set::

   .. tab-item:: Minimal Diagnosis

      .. code-block:: python

         diagnosis = {
             "code": "MYPLUGIN001",
             "loc": ("spec", "templates", 0, "name"),
             "msg": "Templates name 'foo' is not allowed.",
         }

   .. tab-item:: Full Diagnosis

      .. code-block:: python

         diagnosis = {
             "type": "failure",
             "code": "MYPLUGIN001",
             "loc": ("spec", "templates", 0, "name"),
             "summary": "Invalid template name",
             "msg": "Templates name 'foo' is not allowed.",
             "input": "foo",
             "fix": "bar",
         }

Utilities such as :func:`~tugboat.utils.prepend_loc` help apply shared prefixes while iterating over nested structures.
Tugboat already reserves the :doc:`WF <../rules/workflow>` / :doc:`TPL <../rules/template>` / :doc:`STP <../rules/step>` ranges for built-in analyzers, so keep plugin codes separate.


Shared Helpers
--------------

Tugboat includes reusable helpers in several modules to streamline rule development:

- :mod:`tugboat.constraints` validates common field rules (e.g. :func:`~tugboat.constraints.require_all`).
- :mod:`tugboat.references` verifies cross-references such as argument resolution.
- :mod:`tugboat.utils` includes helpers for deduplicating names, joining text, and translating Pydantic validation errors.

These helpers return diagnoses (or iterables), so :py:keyword:`yield from <yield>` them directly to keep rules concise and wording consistent.


Example: Flag Empty Template Names
----------------------------------

The snippet below shows a rule that verifies every template has a name:

.. code-block:: python

   from tugboat import hookimpl
   from tugboat.schemas import Template, Workflow, WorkflowTemplate

   @hookimpl(specname="analyze_template")
   def check_template_name(template: Template, workflow: Workflow | WorkflowTemplate):
       if not template.name:
           yield {
               "code": "MYPLUGIN001",
               "loc": ["name"],
               "msg": "Templates must define a unique name.",
           }

The ``workflow`` argument gives context about the parent manifest.
If you do not need it, like this example, you can omit it from the function signature.
