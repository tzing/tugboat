Ignoring Violations
===================

Tugboat allows you to ignore specific violations in your Argo workflow manifest.
This feature is useful when you encounter violations that are intentional or not relevant to your workflow, enabling you to focus on resolving the most critical issues.

Currently, Tugboat supports ignoring violations by adding comments to your manifest.
Additional methods for managing violations may be introduced in future versions.


Using ``noqa`` comment
----------------------

To ignore violations, add a comment in the format below to the relevant section of your Argo workflow manifest.
The comment may include the rule codes (separated by commas) for the violations you want to ignore.

.. code-block:: yaml
   :caption: Syntax

   # noqa: <code1>, <code2>, ...; <reason>

* The comment must start with ``# noqa``, and the keyword is case-insensitive.
* To ignore multiple rule codes, list them separated by commas after ``# noqa``. The rule codes are case-insensitive.
* Optionally, you can include a reason for ignoring the violations to clarify the rationale for others.
  The reason should follow a semicolon after the rule codes.
  Providing a reason is highly recommended for better maintainability and collaboration.

The comment should be placed on the same line as the section where the violation occurs, or the parent level of the section.

The following example demonstrates how to ignore :ref:`code.var002` in the Argo workflow manifest.
We want to ignore this violation because the template file is intended to be a Jinja template, rather than an Argo tag template.

.. code-block:: yaml
   :caption: Example
   :emphasize-lines: 14

   apiVersion: argoproj.io/v1alpha1
   kind: Workflow
   metadata:
     generateName: examples-
   spec:
     entrypoint: render
     templates:
       - name: render
         inputs:
           artifacts:
             - name: template
               path: /tmp/template.j2
               raw:
                 data: | # noqa: VAR002; this is a Jinja template
                   Hello {{name}}
             - name: data
               path: /tmp/data.json
               raw:
                 data: |
                   {"name": "world"}
         container:
           image: example.com/jinja:latest
           command:
             - jinja2
           args:
             - "{{ inputs.artifacts.template.path }}"
             - "{{ inputs.artifacts.data.path }}"

Known issue: Comment placement
++++++++++++++++++++++++++++++

If a ``# noqa`` comment does not seem to work, consider moving it to a higher-level section of the manifest.

This workaround addresses a known issue with the YAML parser in Tugboat, which may not correctly interpret comments in some cases.

For example, if the violation originates from a ``data`` field, placing the ``# noqa`` comment at the ``artifacts`` level (its parent) can bypass the violation:

.. code-block:: yaml
   :emphasize-lines: 4-5,9

     templates:
       - name: render
         inputs:
           # noqa: VAR002
           artifacts:
             - name: template
               path: /tmp/template.j2
               raw:
                 data: |
                   Hello {{name}}
