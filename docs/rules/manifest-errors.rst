M - Manifest Errors
===================

Code ``M`` is used for errors reported by the manifest parser.
These errors are typically caused by incorrect syntax or missing required information in the manifest file.


``M001`` - Malformed manifest
-----------------------------

The input manifest does not adhere to the expected format.

This error code encompasses all issues identified by the static manifest parsers. Common causes include:

- Missing or incorrect syntax
- Omission of required information
- Improper structure, such as incorrect hierarchy levels

For example, the following manifest is missing the required ``source`` field under the ``script`` section:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     templates:
       - name: hello
         script:
           image: alpine:latest


``M002`` - Unsupported manifest kind
------------------------------------

The input manifest kind is not supported by the parser.

Tugboat is not designed to parse every possible Kubernetes resource.
This error code is triggered when the parser encounters a manifest kind that is not supported by Tugboat.
