Changelog
=========

Unreleased
----------

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
