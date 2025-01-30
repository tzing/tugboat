Manifest Errors (``M``)
=======================

Code ``M`` is primarily used for errors reported by the manifest parser.
These errors are typically caused by incorrect syntax or missing required information in the manifest file.


:bdg:`M001` Not a Kubernetes manifest
-------------------------------------

This error code is triggered when the input file does not look like a Kubernetes manifest.


:bdg:`M002` Unsupported manifest kind
-------------------------------------

The input manifest kind is not supported by the parser.

Tugboat is not designed to parse every possible Kubernetes resource.
This error code is triggered when the parser encounters a manifest kind that is not supported by Tugboat.


.. _code.m003:

:bdg:`M003` Malformed manifest
------------------------------

The input manifest does not conform to the expected format.

This error code is triggered when the parser encounters a general error in the manifest file.
If the parser identifies a more specific issue, a more precise error code, such as :ref:`code.m004`, will be used instead.


.. _code.m004:

:bdg:`M004` Missing required field
----------------------------------

A mandatory field is missing from the resource.

For instance, the following manifest lacks the required ``source`` field within the ``script`` section:

.. code-block:: yaml
   :emphasize-lines: 8-9

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     templates:
       - name: hello
         script:
           image: alpine:latest

.. _code.m005:

:bdg:`M005` Found redundant field
---------------------------------

The manifest contains an unexpected field.

For instance, the following manifest contains an extra field, ``extraField``, within the root of the document:

.. code-block:: yaml
   :emphasize-lines: 10

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

.. _code.m006:

:bdg:`M006` Mutually exclusive fields
-------------------------------------

The manifest contains fields that are mutually exclusive.

For instance, the following manifest contains both ``script`` and ``container`` fields within the same template:

.. code-block:: yaml
   :emphasize-lines: 8,12

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


.. _code.m007:

:bdg:`M007` Type mismatch
-------------------------

The value of a field does not match the expected type.

The following manifest contains a number in ``entrypoint`` field, which is expected to be a string:

.. code-block:: yaml
   :emphasize-lines: 6

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: hello-
   spec:
     entrypoint: 1234


.. _code.m008:

:bdg:`M008` Invalid field value
-------------------------------

The value of a field is not valid.

For instance, the following manifest contains an invalid value for the ``imagePullPolicy`` field:

.. code-block:: yaml
   :emphasize-lines: 10

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


.. _code.m009:

:bdg:`M009` Resource name length error
--------------------------------------

The resource name does not meet the required length criteria; it is either too long or too short.

For generated names, Kubernetes typically trims the user-provided name to fit within the length limit.
However, tugboat requires that the user-provided name reserves 5 characters for the generated suffix to ensure it is not truncated.

For example, the following resource name is too long for a WorkflowTemplate, which has a maximum name length of 63 characters.
This given name (59 characters) may cause the last character of the given name to be truncated:

.. code-block:: yaml
   :emphasize-lines: 4

   apiVersion: argoproj.io/v1alpha1
   kind: WorkflowTemplate
   metadata:
     generateName: an-extreme-long-name-which-exceeds-the-maximum-name-length-
   spec:
     ...


.. _code.m010:

:bdg:`M010` Invalid resource name
---------------------------------

The resource name contains invalid characters.

Kubernetes requires most resource names to comply with the `RFC 1123`_ standard for DNS subdomain names [#kube-names]_:

* Only lowercase alphanumeric characters, ``-``, or ``.``
* Must start with an alphanumeric character
* Must end with an alphanumeric character

.. code-block:: yaml
   :emphasize-lines: 4

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     name: invalid_name
   spec:
     ...

In this example, the resource name ``invalid_name`` contains an underscore, which is not allowed.

.. _RFC 1123: https://tools.ietf.org/html/rfc1123
.. [#kube-names] Read `Object Names and IDs <https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#names>`_ for more details.
