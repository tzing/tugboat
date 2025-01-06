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

           follow_symlinks = true
           output_format = "console"

           [console_output]
           snippet_lines_ahead = 3
           snippet_lines_behind = 3

    .. tab-item:: pyproject.toml
        :sync: pyproject.toml

        .. code-block:: toml

           [tool.tugboat]
           follow_symlinks = true
           output_format = "console"

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

   export TUGBOAT_OUTPUT_FORMAT=junit

For nested configuration keys, use double underscores to separate the keys.
For example, the :confval:`snippet_lines_ahead` configuration can be set using:

.. code-block:: bash

   export TUGBOAT_CONSOLE_OUTPUT__SNIPPET_LINES_AHEAD=5


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

.. confval:: follow_symlinks
   :default: ``false``

   Follow symbolic links when searching for files.

.. confval:: output_format
   :default: ``console``

   The output serialization format can be specified using the following options:

   - ``console``: Outputs in a human-readable text format.
   - ``junit``: Outputs in JUnit XML format, suitable for use with CI/CD systems. For more information, see :doc:`advanced/junit.rst`.


``console_output`` section
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. confval:: snippet_lines_ahead
   :default: ``2``

   The number of lines to include before the diff snippet.

.. confval:: snippet_lines_behind
   :default: ``2``

   The number of lines to include after the diff snippet.
