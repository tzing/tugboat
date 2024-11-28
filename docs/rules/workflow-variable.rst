Workflow Variable Rules (``VAR``)
=================================

The code ``VAR`` identifies potential issues with `workflow variables`_, including syntax errors, misused functions, and other related problems.

.. _workflow variables: https://argo-workflows.readthedocs.io/en/latest/variables/


:bdg:`VAR001` Syntax error
--------------------------

This error occurs when a workflow variable contains any syntax error.

Note that most parsers report syntax errors as soon as they encounter the first issue.
This means the error message might not always indicate the exact location of the problem, but it provides a useful starting point for debugging.


:bdg:`VAR002` Misused reference
-------------------------------

A reference used in the manifest is not defined in the current context.

Tugboat checks the references used in the manifest against a list of references from the `official documentation <https://argo-workflows.readthedocs.io/en/latest/variables/#reference>`_.
If a reference used in the manifest is not found in the defined references, an error is reported.

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: test-
   spec:
     entrypoint: whalesay
     templates:
       - name: whalesay
         inputs:
           artifacts:
             - name: message
               raw:
                 data: Hello Tugboat!
         container:
           image: docker/whalesay:latest
           command: [cowsay]
           args: ["{{ inputs.artifacts.message }}"]
           #       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           #       Reference not found - We can't reference artifact here
