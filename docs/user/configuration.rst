Configurations
==============

Tugboat can be configured in a few different ways.
The most common way is to use a configuration file, but you can also use environment variables or command line arguments.


Config file discovery
---------------------

Tugboat searches for the closest configuration file named ``.tugboat.toml`` or ``pyproject.toml`` in the current directory and all parent directories.

Both files utilize the `TOML`_ format and share the same configuration options.
The distinction is that the ``pyproject.toml`` file adheres to :pep:`518`, requiring all configurations to be placed under the ``tool.tugboat`` section.

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


Environment variables
---------------------

Configuration options can also be set using environment variables.

These environment variables are prefixed with ``TUGBOAT_``, and the configuration keys are case-insensitive.
For example, the :confval:`output_format` configuration can be set using:

.. code-block:: bash

   export tugboat_output_format=junit

For nested configuration keys, use double underscores (``__``) to separate the keys.
For example, the :confval:`snippet_lines_ahead` configuration is under the `console_output section`_, so it can be set using:

.. code-block:: bash

   export TUGBOAT_CONSOLE_OUTPUT__SNIPPET_LINES_AHEAD=5

Some configuration options request a list of values. In this case, the value should be JSON-formatted:

.. code-block:: bash

   export TUGBOAT_EXCLUDE='["helm-chart/templates/**"]'


Settings
--------

Here is a list of all available settings, their default values and descriptions.

Top-level
~~~~~~~~~

.. confval:: color
   :default: ``null``

   Colorize the output.

   - If set to ``true``, the output is always colorized.
   - If set to ``false``, the output is not colorized.
   - If set to ``null``, the output is colorized only when directed to a terminal.

   This option is only utilized when the output format supports colorization.
   Currently, only the ``console`` output format supports colorization.

.. confval:: exclude
   :default: ``[]``

   A list of file paths, directory paths, or patterns to exclude from the check.

   Files or directories matching these paths or patterns will be ignored.
   If a file matches both the :confval:`include` and :confval:`exclude` patterns, it will be excluded.

   For details on pattern matching, refer to the documentation for the :confval:`include` option.

.. confval:: include
   :default: ``["."]`` (all YAML files in the current directory)

   A list of file paths, directory paths, or patterns to include in the check.

   * **File paths:** Specific files will be included in the check.
   * **Directory paths:** All YAML files in the specified directories will be included.
   * **Patterns:** Used to match files. Refer to the pattern matching section for details.

   .. important::

      If a file matches both the :confval:`include` and :confval:`exclude` patterns, it will be excluded from the check.

   Tugboat uses Python's `pattern language`_ to evaluate file paths.
   Supported wildcards in patterns include:

   ``**`` (entire segment)
      Matches any number of file or directory segments, including zero.

   ``*`` (entire segment)
      Matches one file or directory segment.

   ``*`` (part of a segment)
      Matches any number of non-separator characters, including zero.

   ``?``
      Matches one non-separator character.

   ``[seq]``
      Matches one character in seq.

   ``[!seq]``
      Matches one character not in seq.

   .. _pattern language: https://docs.python.org/3.13/library/pathlib.html#pathlib-pattern-language

.. confval:: follow_symlinks
   :default: ``false``

   Follow symbolic links when searching for files.

.. confval:: output_format
   :default: ``console``

   The output serialization format can be specified using the following options:

   - ``console``: Outputs in a human-readable text format.
   - ``junit``: Outputs in JUnit XML format, suitable for use with CI/CD systems. For more information, see :doc:`junit`.


``console_output`` section
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. confval:: snippet_lines_ahead
   :default: ``2``

   The number of lines to include before the diff snippet.

.. confval:: snippet_lines_behind
   :default: ``2``

   The number of lines to include after the diff snippet.
