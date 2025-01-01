Template Rules (``TPL``)
========================

Code ``TPL`` is used for errors specifically related to the `template`_, the reusable and composable unit of execution in a workflow or workflow template.

.. _template: https://argo-workflows.readthedocs.io/en/latest/fields/#template


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
