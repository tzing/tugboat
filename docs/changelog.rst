Changelog
=========

0.6.3
-----

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
