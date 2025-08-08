from __future__ import annotations

import logging
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

import tugboat.engine
from tugboat.mcp.types import Docstring, Result

logger = logging.getLogger(__name__)
server = FastMCP("tugboat")


@server.tool(
    annotations=ToolAnnotations(
        title="Analyze Manifest",
        readOnlyHint=True,
        destructiveHint=False,
        openWorldHint=False,
    )
)
def analyze_stream(
    manifest_path: Annotated[
        str,
        Docstring(
            "Path to the manifest file. The file must be a valid Kubernetes manifest file in YAML format. Any templated manifests (e.g., Helm) should be pre-processed before submission."
        ),
    ],
) -> Result:
    """
    A linter to analyze a Argo Workflows manifest file for potential issues.

    ## Example

    Given the input manifest path `/path/to/manifest.yaml`, which contains:

    ```yaml
    apiVersion: argoproj.io/v1alpha1
    kind: Workflow
    metadata:
      generateName: demo-
    spec:
      templates:
        - name: whalesay
          inputs:
            parameters:
              - name: message
                value: Hello Argo!
          container:
            image: docker/whalesay:latest
            command: [cowsay]
            args:
              - "{{ inputs.parameter.message }}"
    ```

    This tool will analyze the manifest and return a JSON object with the following structure:

    ```json
    {"count":2,"issues":[[{"code":"M101","column":5,"fix":null,"input":null,"line":6,"loc":["spec","entrypoint"],"manifest":"demo-","msg":"Field 'entrypoint' is required in the 'spec' section but missing.","summary":"Missing required field 'entrypoint'","type":"failure"},{"code":"VAR002","column":17,"fix":"{{ inputs.parameters.message }}","input":"{{ inputs.parameter.message }}","line":17,"loc":["spec","templates",0,"container","args",0],"manifest":"demo-","msg":"The parameter reference 'inputs.parameter.message' used in template 'whalesay' is invalid.","summary":"Invalid reference","type":"failure"}]]}
    ```
    """
    logger.debug("Linting manifest %s", manifest_path)

    with open(manifest_path) as fd:
        manifest_content = fd.read()

    diagnoses = tugboat.engine.analyze_yaml_stream(manifest_content, manifest_path)

    return Result.model_validate(
        {
            "count": len(diagnoses),
            "issues": diagnoses,
        }
    )
