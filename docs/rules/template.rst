Template Rules (``TPL``)
========================

Code ``TPL`` is used for errors specifically related to `the template <https://argo-workflows.readthedocs.io/en/latest/fields/#template>`_, the reusable and composable unit of execution in a workflow or workflow template.

Argo Workflows offers various types of templates. However, Tugboat currently supports only a few of them:

.. list-table::
    :header-rows: 1

    * - Template Type
      - Schema check [#schm-chk]_
      - Static analysis [#sttc-chk]_ [#stttc-chk-disclaimer]_

    * - Container template
      - :octicon:`alert` Partial; Check against :py:class:`~tugboat.schemas.ContainerTemplate`
      - :octicon:`check`

    * - `Container set template <https://argo-workflows.readthedocs.io/en/latest/container-set-template/>`_
      - :octicon:`alert` Partial; Check against :py:class:`~tugboat.schemas.template.container.ContainerSetTemplate`
      - :octicon:`check`

    * - `DAG template <https://argo-workflows.readthedocs.io/en/latest/walk-through/dag/>`_
      - :octicon:`alert` Partial; Check against :py:class:`~tugboat.schemas.DagTask`
      - :octicon:`x`

    * - `Data template <https://argo-workflows.readthedocs.io/en/latest/data-sourcing-and-transformation/>`_
      - :octicon:`x`
      - :octicon:`x`

    * - `HTTP template <https://argo-workflows.readthedocs.io/en/latest/http-template/>`_
      - :octicon:`x`
      - :octicon:`x`

    * - `Resource template <https://argo-workflows.readthedocs.io/en/latest/walk-through/kubernetes-resources/>`_
      - :octicon:`x`
      - :octicon:`x`

    * - `Script template <https://argo-workflows.readthedocs.io/en/latest/walk-through/scripts-and-results/>`_
      - :octicon:`alert` Partial; Check against :py:class:`~tugboat.schemas.ScriptTemplate`
      - :octicon:`check`

    * - `Steps template <https://argo-workflows.readthedocs.io/en/latest/walk-through/steps/>`_
      - :octicon:`alert` Partial; Check against :py:class:`~tugboat.schemas.Step`
      - :octicon:`check` Covered by :doc:`step`

    * - `Suspend template <https://argo-workflows.readthedocs.io/en/latest/walk-through/suspending/>`_
      - :octicon:`check` (:py:class:`~tugboat.schemas.template.SuspendTemplate`)
      - :octicon:`x`

.. [#schm-chk] The schema check validates the manifest against the schema defined in the official `field reference`_ document. It identifies missing or extra fields, incorrect data types, and other basic errors. These errors will be reported as :doc:`manifest-errors`.
.. [#sttc-chk] The static analysis examines the manifest's fields and values according to a set of rules. It detects unusual values, misused parameters, and potential runtime issues like duplicate names.
.. [#stttc-chk-disclaimer] Even thought a category is marked as *checked*, it does not mean that all possible issues are covered. Feel free to `create an feature request <https://github.com/tzing/tugboat/issues>`_ or contribute to the project to improve the coverage.
.. _Field Reference: https://argo-workflows.readthedocs.io/en/latest/fields/


:bdg:`TPL001` Duplicate template names
--------------------------------------

The workflow or workflow template contains multiple templates with the same name.

In the following example, the template ``hello`` is duplicated:

.. code-block:: yaml
   :emphasize-lines: 7,10

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
       - name: hello
         container:
           image: alpine:latest
       - name: hello
         container:
           image: busybox:latest


:bdg:`TPL002` Duplicate input parameter names
---------------------------------------------

The template contains multiple input parameters (``<template>.inputs.parameters``) with the same name.

.. code-block:: yaml
   :emphasize-lines: 10,11

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
       - name: main
         inputs:
           parameters:
             - name: data
             - name: data
         ...


:bdg:`TPL003` Duplicate input artifact names
--------------------------------------------

The template contains multiple input artifacts (``<template>.inputs.artifacts``) with the same name.

.. code-block:: yaml
   :emphasize-lines: 10,12

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
       - name: main
         inputs:
           artifacts:
             - name: data
               path: /data/foo
             - name: data
               path: /data/bar
         ...


:bdg:`TPL004` Duplicate output parameter names
----------------------------------------------

The template contains multiple output parameters (``<template>.outputs.parameters``) with the same name.

.. code-block:: yaml
   :emphasize-lines: 11,14

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
        - name: main
          ...
          outputs:
            parameters:
              - name: message
                valueFrom:
                  path: /tmp/message.txt
              - name: message
                valueFrom:
                  path: /tmp/msg.txt


:bdg:`TPL005` Duplicate output artifact names
---------------------------------------------

The template contains multiple output artifacts (``<template>.outputs.artifacts``) with the same name.

.. code-block:: yaml
   :emphasize-lines: 11,13

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     name: demo
   spec:
     templates:
        - name: main
          ...
          outputs:
            artifacts:
              - name: data
                path: /data/foo
              - name: data
                path: /data/bar
