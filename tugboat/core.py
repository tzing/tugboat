from __future__ import annotations

import functools

import pluggy

hookimpl = pluggy.HookimplMarker("tugboat")
"""The hook implementation marker for the Tugboat framework."""


@functools.lru_cache(1)
def get_plugin_manager() -> pluggy.PluginManager:
    pm = pluggy.PluginManager("tugboat")
    pm.load_setuptools_entrypoints("tugboat")

    # hook specs
    import tugboat.hookspecs.core
    import tugboat.hookspecs.workflow

    pm.add_hookspecs(tugboat.hookspecs.core)
    pm.add_hookspecs(tugboat.hookspecs.workflow)

    # built-in hook implementations
    import tugboat.analyzers.container
    import tugboat.analyzers.cron_workflow
    import tugboat.analyzers.step
    import tugboat.analyzers.template
    import tugboat.analyzers.template.inputs
    import tugboat.analyzers.template.outputs
    import tugboat.analyzers.workflow
    import tugboat.analyzers.workflow_template
    import tugboat.schemas

    pm.register(tugboat.analyzers.container)
    pm.register(tugboat.analyzers.cron_workflow)
    pm.register(tugboat.analyzers.step)
    pm.register(tugboat.analyzers.template)
    pm.register(tugboat.analyzers.template.inputs)
    pm.register(tugboat.analyzers.template.outputs)
    pm.register(tugboat.analyzers.workflow)
    pm.register(tugboat.analyzers.workflow_template)
    pm.register(tugboat.schemas)

    return pm
