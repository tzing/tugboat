Changelog
=========

Unreleased
----------

:octicon:`codescan-checkmark` Rules
+++++++++++++++++++++++++++++++++++

* New rule set :doc:`rules/dag` to validate DAG templates and their tasks.
* Redesign :doc:`rules/variable` to improve validation of Argo workflow variable references:

  * Rule ``VAR001`` has been renamed to :rule:`var101`.
  * Rule ``VAR002`` has been renamed to :rule:`var201`.
  * New rule :rule:`var102` to flag invalid usage of expr-lang format in simple tags.
  * New rule :rule:`var202` to flag non-Argo variable references.

:octicon:`plug` Enhancements
++++++++++++++++++++++++++++

* Use JSONPath-like syntax for specifying locations in output reports.

:octicon:`code-review` API Changes
++++++++++++++++++++++++++++++++++

* The :py:attr:`Diagnosis.fix <tugboat.Diagnosis.fix>` field now accepts :py:class:`dict` types in addition to :py:class:`str`.
  Use :py:class:`dict` when suggesting fixes that involve multiple fields or complex object replacements, while :py:class:`str` remain suitable for simple value corrections.
* Refactor :py:mod:`tugboat.constraints` to provide more flexible validation functions:

  * Diagnostic messages have been improved for clarity.
  * The ``loc`` parameter is now optional and defaults automatically.
  * :py:func:`~tugboat.constraints.mutually_exclusive` now supports exact-one validation.
  * :py:func:`~tugboat.constraints.require_all` accepts an ``accept_empty`` parameter.
  * ``require_non_empty`` and ``require_exactly_one`` have been removed in favor of the expanded functions above.

* Remove :py:mod:`tugboat.utils.pydantic` module

:octicon:`bug` Fixes
++++++++++++++++++++

* Fix the output crash when the diagnosis source location is at the end of a file.

0.6.2
-----

:octicon:`plug` Enhancements
++++++++++++++++++++++++++++

* Redesign the validator for :py:class:`~tugboat.schemas.Artifact` and :py:class:`~tugboat.schemas.Parameter` to improve clarity and maintainability.

:octicon:`bug` Fixes
++++++++++++++++++++

* Prevent crashes when resolving source locations where the recorded path is empty.

0.6.1
-----

:octicon:`codescan-checkmark` Rules
+++++++++++++++++++++++++++++++++++

* Enforce :py:attr:`~tugboat.schemas.Artifact.path` on input artifacts for container/script templates and flag it on incompatible templates.
* Restrict output parameter :py:attr:`~tugboat.schemas.Parameter.valueFrom` fields by template type.
* Require output artifacts to source data correctly, enforcing :py:attr:`~tugboat.schemas.Artifact.path` usage for container/script templates and forbidding it on others.

:octicon:`plug` Enhancements
++++++++++++++++++++++++++++

* The helper functions :py:func:`~tugboat.utils.join_with_and` and :py:func:`~tugboat.utils.join_with_or` now automatically sort their input lists.


0.6.0
-----

:octicon:`rocket` New
+++++++++++++++++++++

* Support :doc:`mcp` for better integration with IDEs and coding agents.
* Parse Helm's leading ``# Source:`` comments to provide more context in reports.

:octicon:`plug` Enhancements
++++++++++++++++++++++++++++

* Redesign the outputs, including:

  * Improve the looks of the console output.
  * Tweak the attribute name in JUnit XML reports to be more compatible with various tools.
  * Add GitHub Actions output format for better integration with GitHub workflows.

* Support `FORCE_COLOR <https://force-color.org/>`_ and `NO_COLOR <https://no-color.org/>`_ environment variables to control color output.

Prior to 0.6
------------

Everything before 0.6 has turned to cosmic dust - lost to time and memory.
