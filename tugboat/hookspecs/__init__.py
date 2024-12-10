"""
:py:mod:`tugboat.hookspecs` manages the hook specifications for Tugboat.
It is used to define the hooks that can be implemented by plugins.

The hooks are defined as functions with specific signatures.
Tugboat calls these hooks during the linting process.

The Tugboat framework heavily relies on :py:mod:`pluggy` for hook management.
For details on how to implement hooks, please refer to the
`pluggy's documentation <https://pluggy.readthedocs.io/en/stable/>`_.
"""
