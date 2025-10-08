Configurations
==============

Tugboat reads settings from configuration files, environment variables, and command-line flags.
Most teams rely on a shared config file, with env vars or flags layered on top when they need overrides.


Config File Discovery
---------------------

Starting from the working directory, Tugboat walks up each parent folder until it finds a ``.tugboat.toml`` or ``pyproject.toml``.

Both files use the `TOML`_ format and expose the same settings.
When you use ``pyproject.toml``, follow :pep:`518` and place the keys under ``tool.tugboat``.

Here is an example configuration file:

.. tab-set::
    :sync-group: config-format

    .. tab-item:: TOML
        :sync: toml

        .. code-block:: toml

           output_format = "console"
           exclude = ["helm-chart/templates/**"]

           [console_output]
           snippet_lines_ahead = 3
           snippet_lines_behind = 3

    .. tab-item:: pyproject.toml
        :sync: pyproject.toml

        .. code-block:: toml

           [tool.tugboat]
           output_format = "console"
           exclude = ["helm-chart/templates/**"]

           [tool.tugboat.console_output]
           snippet_lines_ahead = 3
           snippet_lines_behind = 3

.. _TOML: https://toml.io/en/


Environment Variables
---------------------

Set any configuration with an environment variable.

Basics:

* Prefix the variable name with ``TUGBOAT_``.
* Configuration keys ignore case.

For example, set :confval:`output_format` with:

.. code-block:: bash

   export tugboat_output_format=junit

Nested configuration keys use double underscores (``__``) between each level.
Because :confval:`snippet_lines_ahead` lives in the `console_output section`_, you can set it with:

.. code-block:: bash

   export TUGBOAT_CONSOLE_OUTPUT__SNIPPET_LINES_AHEAD=5

When an option expects a list, provide the value as JSON:

.. code-block:: bash

   export TUGBOAT_EXCLUDE='["helm-chart/templates/**"]'


Settings
--------

Here are the available settings, their default values, and what they control.

Top-level
~~~~~~~~~

.. confval:: color
   :default: ``null``

   Controls whether Tugboat colorizes its output.

   - ``true``: always use color.
   - ``false``: never use color.
   - ``null``: use color only when writing to a terminal.

   Color is currently supported only when :confval:`output_format` is ``console``.

   Tugboat respects both `NO_COLOR`_ and `FORCE_COLOR`_ environment variables. These may override the :confval:`color` setting.

   .. _NO_COLOR: https://no-color.org/
   .. _FORCE_COLOR: https://force-color.org/

.. confval:: exclude
   :default: ``[]``

   Skip files, folders, or glob patterns by listing them here.

   If a path matches both :confval:`include` and :confval:`exclude`, exclusion wins.
   See `path globbing`_ for details on pattern syntax.

.. confval:: include
   :default: ``["."]`` (all YAML files in the current directory)

   Choose which files Tugboat checks.

   * **File paths:** select specific files.
   * **Directory paths:** include all YAML files under the directory.
   * **Patterns:** glob-style patterns (see `path globbing`_).

   .. important::

      If a file matches both :confval:`include` and :confval:`exclude`, the file is excluded.

.. confval:: follow_symlinks
   :default: ``false``

   Follow symbolic links when scanning for files.

.. confval:: output_format
   :default: ``console``

   Choose how Tugboat formats its results:

   - ``console``: human-friendly text.
   - ``junit``: JUnit XML for CI systems; see :doc:`junit` for details.


``console_output`` section
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. confval:: snippet_lines_ahead
   :default: ``2``

   The number of lines to include before the diff snippet.

.. confval:: snippet_lines_behind
   :default: ``2``

   The number of lines to include after the diff snippet.

Path Globbing
-------------

Tugboat reuses Python's `pattern language`_ for matching file paths. Supported wildcards include:

``**`` (entire segment)
   Matches zero or more path segments.

``*`` (entire segment)
   Matches exactly one path segment.

``*`` (part of a segment)
   Matches any number of non-separator characters.

``?``
   Matches a single non-separator character.

``[seq]``
   Matches a single character from ``seq``.

``[!seq]``
   Matches a single character not in ``seq``.

Here are some examples:

* ``*.yaml`` matches all YAML files in the current directory.
* ``**/*.yaml`` matches all YAML files in the current directory and all subdirectories.

.. _pattern language: https://docs.python.org/3.13/library/pathlib.html#pathlib-pattern-language
