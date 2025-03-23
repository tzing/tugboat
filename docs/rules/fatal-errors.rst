Fatal Errors (``F``)
====================

Code ``F`` are the most severe errors that stops the analysis.
They are usually related to the manifest file parsing errors, or the manifest is not valid.

.. rule:: F001 Internal error

   An exception occurred during the analysis.
   Please `report this issue <https://github.com/tzing/tugboat/issues>`_ to Tugboat developers.

.. rule:: F002 Malformed YAML document

   The given manifest file is not a valid YAML file.

.. rule:: F003 Malformed document structure

   The provided manifest file content is not structured as a mapping.

   This issue may arise if the manifest file is empty or if it is formatted as a sequence.

   A valid Kubernetes manifest file should be a mapping, meaning it should start with ``---`` if it contains multiple documents.
