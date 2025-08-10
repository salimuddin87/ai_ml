# MCP Introduction
CP provides a standardized way to connect AI models to different data sources and tools.
It allows models to access and utilize shared context, improving their performance and capabilities.

## General Architecture
At its core, MCP follows a client-server architecture where a host application can connect to multiple servers:

![mcp architecture](C:\Users\md_salimuddin_ansari\PycharmProjects\ai_ml\MCP\images\mcp_architecture.png)

* **MCP Hosts**: Programs like Claude Desktop, IDEs, or AI tools that want to access data through MCP
* **MCP Clients**: Protocol clients that maintain 1:1 connections with servers
* **MCP Servers**: Lightweight programs that each expose specific capabilities through the standardized Model Context Protocol
* **Local Data Sources**: Your computer’s files, databases, and services that MCP servers can securely access
* **Remote Services**: External systems available over the internet (e.g., through APIs) that MCP servers can connect to

# Quickstart
## For Server Developers
We’ll build a server that exposes two tools: `get-alerts` and `get-forecast`. Then we’ll connect the server to an MCP host (in this case, `Claude for Desktop`):

### MCP servers can provide three main types of capabilities:
1. **Resources**: File-like data that can be read by clients (like API responses or file contents)
2. **Tools**: Functions that can be called by the LLM (with user approval)
3. **Prompts**: Pre-written templates that help users accomplish specific tasks

Example -> https://github.com/modelcontextprotocol/quickstart-resources/tree/main/weather-server-python

## For Client Developers
1. Client Initialization
2. Server Connection
3. Query Processing
4. Interactive Interface
5. Resource Management

Example -> https://github.com/modelcontextprotocol/quickstart-resources/tree/main/mcp-client-python

## For Claude Desktop Users


