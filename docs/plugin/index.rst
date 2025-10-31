Writing Plugins
===============

``tugboat`` includes many analyzers, but write a plugin when you need checks that are specific to your environment or you want to iterate separately from the core distribution.

Contribute generally useful rules upstream; otherwise ship them as external plugins to keep the built-ins focused.

Refer to :doc:`../api/tugboat` for the hook signatures and classes mentioned below.


Plugin Architecture
-------------------

Plugins are standard Python packages that `pluggy`_ can discover at runtime.
Tugboat looks for hook implementations registered under the ``tugboat`` entry point group and loads them automatically.

Hook signatures live in :doc:`../api/tugboat.hookspecs`, so review argument names and types there before writing code.
The hook layer keeps your implementation decoupled from tugboat internals, meaning you only need to import the contracts you rely on — usually :py:mod:`tugboat`.

.. _pluggy: https://pluggy.readthedocs.io/en/stable/


Plugin Anatomy
--------------

A minimal plugin exposes a module or class with hook implementations decorated by :data:`tugboat.hookimpl`. Group related checks so :py:mod:`pluggy` loads them together and keeps plugin discovery fast.

A skeleton module might look like:

.. code-block:: python

   from tugboat import hookimpl
   from tugboat.schemas import Workflow
   from tugboat.types import Diagnosis

   @hookimpl
   def analyze_workflow(workflow: Workflow) -> list[Diagnosis]:
       return []

You can split larger plugins into packages, but the entry point must register an object that exposes the hook functions (a module, class, or instance).


Registration
------------

Decorate each hook function or method with :data:`tugboat.hookimpl`; pluggy uses that marker to register your implementation.

Tugboat discovers plugins via entry points named ``tugboat``.
Declare them with whichever packaging tool you use:

.. tab-set::

   .. tab-item:: PEP 621

      .. code-block:: toml

         [project.entry-points."tugboat"]
         my_plugin = "my_plugin.rules"

   .. tab-item:: Poetry

      .. code-block:: toml

         [tool.poetry.plugins."tugboat"]
         my_plugin = "my_plugin.rules"

   .. tab-item:: setuptools (setup.cfg)

      .. code-block:: ini

         [options.entry_points]
         tugboat =
             my_plugin = my_plugin.rules

   .. tab-item:: setuptools (setup.py)

      .. code-block:: python

         from setuptools import setup

         setup(
             name="my-plugin",
             entry_points={
                 "tugboat": [
                     "my_plugin = my_plugin.rules",
                 ],
             },
         )

During development, install the project in editable mode (for example ``poetry install`` or ``pip install -e .``) so tugboat picks up code changes without a fresh install.


What's Next?
------------

.. toctree::

   rules
