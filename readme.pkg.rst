Tugboat
=======

   The tugboat guides the ship to flight, from harbor's hold to ocean's light.

Tugboat is a linter to streamline your `Argo Workflows <https://argoproj.github.io/workflows/>`_ with precision and confidence.

.. code-block:: none

   $ tugboat
   WF201 Invalid entrypoint
     @whalesay.yaml:6:15 (test-)

     4 |   generateName: test-
     5 | spec:
     6 |   entrypoint: ducksay
       |               ^^^^^^^
       |               └ WF201 at .spec.entrypoint
     7 |   templates:
     8 |     - name: whalesay

     Entrypoint 'ducksay' is not defined in any template.
     Defined entrypoints: 'whalesay'

     Do you mean: whalesay

   Found 1 failures
