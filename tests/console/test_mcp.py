import json
import textwrap
from pathlib import Path

import fastmcp
import mcp.types
import pytest
from dirty_equals import IsPartialDict

from tugboat.console.mcp import server


@pytest.mark.asyncio
async def test_list_tools():
    (tool,) = await server.list_tools()
    assert tool.name == "analyze_stream"


@pytest.mark.asyncio
async def test_analyze_stream(tmp_path: Path):
    MANIFEST = textwrap.dedent(
        """
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
        """
    )

    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(MANIFEST)

    async with fastmcp.Client(server) as client:
        result = await client.call_tool(
            "analyze_stream",
            {
                "manifest_path": str(manifest_path),
            },
        )

    assert len(result.content) == 1
    assert isinstance(result.content[0], mcp.types.TextContent)

    response = json.loads(result.content[0].text)
    assert response == {
        "count": 2,
        "issues": [
            IsPartialDict(
                {
                    "code": "M101",
                    "sourceNearby": "spec:\n  templates:\n    - name: whalesay\n      inputs:",
                    "loc": ["spec", "entrypoint"],
                }
            ),
            IsPartialDict(
                {
                    "code": "VAR002",
                    "sourceNearby": '        args:\n          - "{{ inputs.parameter.message }}"',
                    "loc": ["spec", "templates", 0, "container", "args", 0],
                    "input": "{{ inputs.parameter.message }}",
                    "fix": "{{ inputs.parameters.message }}",
                }
            ),
        ],
    }
