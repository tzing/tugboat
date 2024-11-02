M - Manifest Errors
===================

Code ``M`` is used for errors reported by the manifest parser.
These errors are typically caused by incorrect syntax or missing required information in the manifest file.


``M001`` - Not a Kubernetes manifest
------------------------------------

This error code is triggered when the input file does not look like a Kubernetes manifest.


``M002`` - Unsupported manifest kind
------------------------------------

The input manifest kind is not supported by the parser.

Tugboat is not designed to parse every possible Kubernetes resource.
This error code is triggered when the parser encounters a manifest kind that is not supported by Tugboat.


``M003`` - Malformed manifest
-----------------------------

The input manifest does not conform to the expected format.

This error code is triggered when the parser encounters a general error in the manifest file.
If the parser identifies a more specific issue, a more precise error code, such as :ref:`M004 <error.m004>`, will be used instead.


.. _error.m004:

``M004`` - Missing required field
---------------------------------

A mandatory field is missing from the manifest.

For instance, the following manifest lacks the required ``source`` field within the ``script`` section:

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


``M005`` - Found redundant field
--------------------------------

The manifest contains an unexpected field.

For instance, the following manifest contains an extra field, ``extraField``, within the root of the document:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     templates:
       - name: hello
         container:
           image: alpine:latest
   extraField: value


``M006`` - Mutually exclusive fields
------------------------------------

The manifest contains fields that are mutually exclusive.

For instance, the following manifest contains both ``script`` and ``container`` fields within the same template:

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
           source: |
             echo 'Hello, world!'
         container:
           image: alpine:latest


``M007`` - Type mismatch
------------------------

The value of a field does not match the expected type.

The following manifest contains a number in ``entrypoint`` field, which is expected to be a string:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     entrypoint: 1234


``M008`` - Invalid field value
------------------------------

The value of a field is not valid.

For instance, the following manifest contains an invalid value for the ``imagePullPolicy`` field:

.. code-block:: yaml

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     templates:
       - name: hello
         container:
           image: alpine:latest
           imagePullPolicy: InvalidValue
