import json
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
async def test_analyze_stream(fixture_dir: Path):
    async with fastmcp.Client(server) as client:
        result = await client.call_tool(
            "analyze_stream",
            {
                "manifest_path": str(fixture_dir / "missing-script-source.yaml"),
            },
        )

    content = result.content[0]
    assert isinstance(content, mcp.types.TextContent)
    assert json.loads(content.text) == {
        "count": 1,
        "issues": [
            IsPartialDict({"code": "M101"}),
        ],
    }
