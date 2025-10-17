Model Context Protocol (MCP)
============================

Tugboat is designed to streamline the development of Argo Workflows manifests, making the process faster and more efficient.
We're also focused on making it easy and intuitive to use.

With AI agents quickly becoming a new standard in modern software development, we're excited about the potential they bring to everyday workflows.
To support this shift, Tugboat now exposes its capabilities through the `Model Context Protocol (MCP)`_ — the bridge that enables smooth and consistent interaction between developers, tools, and AI agents.

.. _Model Context Protocol (MCP): https://modelcontextprotocol.io/overview


Starting the Server
-------------------

You can use `pipx`_ or `uv`_ to run the Tugboat MCP server:

.. tab-set::

   .. tab-item:: pipx :iconify:`simple-icons:pipx`

      .. code-block:: bash

         pipx run 'argo-tugboat[mcp]' --mcp

   .. tab-item:: uv :iconify:`simple-icons:uv`

      .. code-block:: bash

         uvx --from='argo-tugboat[mcp]' tugboat --mcp

.. _pipx: https://pipx.pypa.io/stable/
.. _uv: https://docs.astral.sh/uv/


Use with Agents
---------------

Claude Code
^^^^^^^^^^^

:octicon:`book` `Connect Claude Code to tools via MCP <https://docs.claude.com/en/docs/claude-code/mcp#mcp-installation-scopes>`_

.. code-block:: bash

   # run this command in your terminal
   claude mcp add tugboat -- uvx --from='argo-tugboat[mcp]' tugboat --mcp

Cursor :iconify:`material-icon-theme:cursor-light`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: https://cursor.com/deeplink/mcp-install-dark.svg
   :target: cursor://anysphere.cursor-deeplink/mcp/install?name=tugboat&config=eyJjb21tYW5kIjoidXYgdG9vbCBydW4gLS1mcm9tPWFyZ28tdHVnYm9hdFttY3BdIHR1Z2JvYXQgLS1tY3AifQ%3D%3D
   :alt: Install MCP Server

:octicon:`book` `Cursor MCP Documentation <https://docs.cursor.com/context/model-context-protocol>`_

.. code-block:: json
   :caption: .cursor/mcp.json

   {
     "mcpServers": {
       "tugboat": {
         "type": "stdio",
         "command": "uv",
         "args": [
           "tool",
           "run",
           "--from=argo-tugboat[mcp]",
           "tugboat",
           "--mcp"
         ]
       }
     }
   }

Gemini CLI
^^^^^^^^^^

:octicon:`book` `MCP servers with the Gemini CLI <https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html>`_

.. code-block:: json
   :caption: .gemini/settings.json

   {
     "mcpServers": {
       "tugboat": {
         "command": "uv",
         "args": [
           "tool",
           "run",
           "--from=argo-tugboat[mcp]",
           "tugboat",
           "--mcp"
         ]
       }
     }
   }

OpenAI Codex
^^^^^^^^^^^^

:octicon:`book` `OpenAI Codex MCP Documentation <https://github.com/openai/codex/blob/main/docs/advanced.md#model-context-protocol-mcp>`_

.. code-block:: toml
   :caption: ~/.codex/config.toml

   [mcp_servers.tugboat]
   command = "uv"
   args = ["tool", "run", "--from=argo-tugboat[mcp]", "tugboat", "--mcp"]

VS Code :iconify:`simple-icons:visualstudiocode`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: https://img.shields.io/badge/VS_Code-Install_Tugboat_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=ffffff
   :target: vscode:mcp/install?%7B%22name%22%3A%22tugboat%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uv%22%2C%22args%22%3A%5B%22tool%22%2C%22run%22%2C%22--from%3Dargo-tugboat%5Bmcp%5D%22%2C%22tugboat%22%2C%22--mcp%22%5D%7D
   :alt: Install in VS Code

.. image:: https://img.shields.io/badge/VS_Code_Insiders-Install_Tugboat_MCP-24bfa5?style=flat-square&logo=visualstudiocode&logoColor=ffffff
   :target: vscode-insiders:mcp/install?%7B%22name%22%3A%22tugboat%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uv%22%2C%22args%22%3A%5B%22tool%22%2C%22run%22%2C%22--from%3Dargo-tugboat%5Bmcp%5D%22%2C%22tugboat%22%2C%22--mcp%22%5D%7D
   :alt: Install in VS Code Insiders

:octicon:`book` `Use MCP servers in VS Code <code.visualstudio.com/docs/copilot/customization/mcp-servers>`_

.. code-block:: json
   :caption: .vscode/mcp.json

   {
     "servers": {
       "tugboat": {
         "type": "stdio",
         "command": "uv",
         "args": [
           "tool",
           "run",
           "--from=argo-tugboat[mcp]",
           "tugboat",
           "--mcp"
         ]
       }
     }
   }
