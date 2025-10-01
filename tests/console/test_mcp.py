import json
import re
import shutil
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock

import fastmcp
import mcp.types
import pytest
import yaml
from dirty_equals import IsPartialDict

from tugboat.console.mcp import render_helm_template, server


@pytest.fixture
def _requires_helm():
    if shutil.which("helm") is None:
        pytest.skip("Helm is not installed")


@pytest.mark.asyncio
async def test_list_tools():
    (tool,) = await server.list_tools()
    assert tool.name == "analyze_stream"


class TestAnalyzeStream:

    @pytest.mark.asyncio
    async def test_plain(self, tmp_path: Path):
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
                    "is_helm_template": False,
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

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_requires_helm")
    async def test_helm(self, argo_example_helm_dir: Path):
        template_path = argo_example_helm_dir / "templates" / "print-message.yaml"

        async with fastmcp.Client(server) as client:
            result = await client.call_tool(
                "analyze_stream",
                {
                    "manifest_path": str(template_path),
                    "is_helm_template": True,
                },
            )

        assert len(result.content) == 1
        assert isinstance(result.content[0], mcp.types.TextContent)

        response = json.loads(result.content[0].text)
        assert response == {"count": 0, "issues": []}

    @pytest.mark.asyncio
    async def test_manifest_not_found(self):
        async with fastmcp.Client(server) as client:
            result = await client.call_tool(
                "analyze_stream",
                {
                    "manifest_path": "/path/that/does/not/exist.yaml",
                    "is_helm_template": False,
                },
            )

        assert len(result.content) == 1
        assert isinstance(result.content[0], mcp.types.TextContent)

        response = json.loads(result.content[0].text)
        assert response == {
            "message": "Manifest not found. Input path: /path/that/does/not/exist.yaml, resolved path: /path/that/does/not/exist.yaml"
        }

    @pytest.mark.asyncio
    async def test_manifest_not_a_file(self, tmp_path: Path):
        async with fastmcp.Client(server) as client:
            result = await client.call_tool(
                "analyze_stream",
                {
                    "manifest_path": str(tmp_path),
                    "is_helm_template": False,
                },
            )

        assert len(result.content) == 1
        assert isinstance(result.content[0], mcp.types.TextContent)

        response = json.loads(result.content[0].text)
        assert response == {
            "message": f"Manifest path is not a file. Input path: {tmp_path}, resolved path: {tmp_path}"
        }

    @pytest.mark.asyncio
    async def test_helm_template_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        monkeypatch.setattr(
            "tugboat.console.mcp.render_helm_template",
            AsyncMock(side_effect=RuntimeError("Mock template error")),
        )

        manifest_path = tmp_path / "template.yaml"
        manifest_path.touch()

        async with fastmcp.Client(server) as client:
            result = await client.call_tool(
                "analyze_stream",
                {
                    "manifest_path": str(manifest_path),
                    "is_helm_template": True,
                },
            )

        assert len(result.content) == 1
        assert isinstance(result.content[0], mcp.types.TextContent)

        response = json.loads(result.content[0].text)
        assert response == {"message": "Mock template error"}


class TestRenderHelmTemplate:

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_requires_helm")
    async def test_success(self, argo_example_helm_dir: Path):
        template_path = argo_example_helm_dir / "templates" / "print-message.yaml"

        content = await render_helm_template(template_path)
        assert isinstance(content, str)

        manifest = yaml.safe_load(content)
        assert manifest == IsPartialDict(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "WorkflowTemplate",
                "metadata": IsPartialDict(
                    {
                        "name": "release-name-argo-workflows-helm-print-message",
                    }
                ),
            }
        )

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_requires_helm")
    async def test_error(self, argo_example_helm_dir: Path):
        template_path = argo_example_helm_dir / "templates" / "invalid.yaml"

        with pytest.raises(
            RuntimeError,
            match=re.escape(
                "Helm template command failed: Error: could not find template templates/invalid.yaml in chart"
            ),
        ):
            await render_helm_template(template_path)

    @pytest.mark.asyncio
    async def test_not_helm_template(self, tmp_path: Path):
        with pytest.raises(
            FileNotFoundError,
            match=re.escape("Could not find Chart.yaml for template path"),
        ):
            await render_helm_template(tmp_path / "manifest.yaml")

    @pytest.mark.asyncio
    async def test_helm_command_not_found(
        self, monkeypatch: pytest.MonkeyPatch, argo_example_helm_dir: Path
    ):
        monkeypatch.setattr(
            "asyncio.create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError)
        )

        with pytest.raises(RuntimeError, match=re.escape("Helm executable not found")):
            await render_helm_template(
                argo_example_helm_dir / "templates" / "print-message.yaml"
            )
