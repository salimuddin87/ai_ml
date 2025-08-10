# Core Architecture
The Model Context Protocol (MCP) is built on a flexible, extensible architecture that enables seamless communication between LLM applications and integrations. This document covers the core architectural components and concepts.

## Overview 
MCP follows a client-server architecture where:
* **_Hosts_** are LLM applications (like Claude Desktop or IDEs) that initiate connections
* **_Clients_** maintain 1:1 connections with servers, inside the host application
* **_Servers_** provide context, tools, and prompts to clients

![Core archtecture](C:\Users\md_salimuddin_ansari\PycharmProjects\ai_ml\MCP\images\mcp_core_architecture.png)

## Core Components
### Protocol layer
The protocol layer handles message framing, request/response linking, and high-level communication patterns.
```python
    class Session(BaseSession[RequestT, NotificationT, ResultT]):
        async def send_request(
            self,
            request: RequestT,
            result_type: type[Result]
        ) -> Result:
            """
            Send request and wait for response. Raises McpError if response contains error.
            """
            # Request handling implementation

        async def send_notification(
            self,
            notification: NotificationT
        ) -> None:
            """Send one-way notification that doesn't expect response."""
            # Notification handling implementation

        async def _received_request(
            self,
            responder: RequestResponder[ReceiveRequestT, ResultT]
        ) -> None:
            """Handle incoming request from other side."""
            # Request handling implementation

        async def _received_notification(
            self,
            notification: ReceiveNotificationT
        ) -> None:
            """Handle incoming notification from other side."""
            # Notification handling implementation
```

### Transport layer
The transport layer handles the actual communication between clients and servers. MCP supports multiple transport mechanisms:
1. Stdio transport
    * Uses standard input/output for communication
    * Ideal for local processes
2. HTTP with SSE transport
   * Uses Server-Sent Events for server-to-client messages
   * HTTP POST for client-to-server messages

All transports use [JSON-RPC](https://www.jsonrpc.org/) 2.0 to exchange messages. See the [specification](https://modelcontextprotocol.info/specification/) for detailed information about the Model Context Protocol message format.

### Message types
MCP defines several message types for communication:
1. **_Request_** expect a response from the other side
2. **_Result_** are successful responses to requests
3. **_Errors_** indicate issues with requests
4. **_Notifications_** are one-way messages that don’t expect a response

## Error handling
MCP defines these standard error codes:
```
enum ErrorCode {
  // Standard JSON-RPC error codes
  ParseError = -32700,
  InvalidRequest = -32600,
  MethodNotFound = -32601,
  InvalidParams = -32602,
  InternalError = -32603
}
```
SDKs and applications can define their own error codes above -32000.

# Prompts
see the example prompts server 

# Resources
Resources represent any kind of data that an MCP server wants to make available to clients. This can include:
* File contents
* Database records
* API responses
* Live system data
* Screenshots and images
* Log files
* And more

Each resource is identified by a unique URI and can contain either text or binary data.

# Roots
Roots are the top-level directories or files that a server exposes to clients. They provide a way to organize and access resources in a structured manner. Each root can contain multiple resources, and clients can navigate through these roots to find the data they need.

Roots are identified by a unique URI and can be used to group related resources together.

### Why Use Roots? 
Roots serve several important purposes:
1. **Guidance**: They inform servers about relevant resources and locations
2. **Clarity**: Roots make it clear which resources are part of your workspace
3. **Organization**: Multiple roots let you work with different resources simultaneously
```
{
  "roots": [
    {
      "uri": "file:///home/user/projects/frontend",
      "name": "Frontend Repository"
    },
    {
      "uri": "https://api.example.com/v1",
      "name": "API Endpoint"
    }
  ]
}
```

# Sampling
Sampling is a technique used to control the randomness and creativity of LLM responses. MCP supports various sampling methods, including:
1. **Temperature**: Controls randomness in responses
   * Higher values (e.g., 0.8) produce more creative outputs
   * Lower values (e.g., 0.2) produce more deterministic outputs
2. **Top-p (nucleus sampling)**: Limits the response to the most probable tokens
3. **Top-k**: Limits the response to the top k most probable tokens
4. **Frequency penalty**: Reduces the likelihood of repeating tokens
5. **Presence penalty**: Increases the likelihood of introducing new tokens
6. **Logit bias**: Adjusts the probability of specific tokens appearing in the response
7. **Stop sequences**: Defines specific tokens that, when generated, will stop the response generation
8. **Max tokens**: Limits the maximum length of the response
9. **Best of**: Generates multiple responses and returns the best one based on a scoring function
10. **Seed**: Sets a random seed for reproducibility of results
11. **Echo**: If set to true, the input prompt is included in the response
12. **Stream**: If set to true, the response is streamed back in chunks instead of all at once

Sampling requests use a standardized message format:
```ignorelang
{
  messages: [
    {
      role: "user" | "assistant",
      content: {
        type: "text" | "image",

        // For text:
        text?: string,

        // For images:
        data?: string,             // base64 encoded
        mimeType?: string
      }
    }
  ],
  modelPreferences?: {
    hints?: [{
      name?: string                // Suggested model name/family
    }],
    costPriority?: number,         // 0-1, importance of minimizing cost
    speedPriority?: number,        // 0-1, importance of low latency
    intelligencePriority?: number  // 0-1, importance of capabilities
  },
  systemPrompt?: string,
  includeContext?: "none" | "thisServer" | "allServers",
  temperature?: number,
  maxTokens: number,
  stopSequences?: string[],
  metadata?: Record<string, unknown>
}
```

# Tools
Tools in MCP allow servers to expose executable functions that can be invoked by clients and used by LLMs to perform actions. Key aspects of tools include:
* **Discovery**: Clients can list available tools through the tools/list endpoint
* **Invocation**: Tools are called using the tools/call endpoint, where servers perform the requested operation and return results
* **Flexibility**: Tools can range from simple calculations to complex API interactions

Each tool is defined with the following structure:
```ignorelang
{
  name: string;          // Unique identifier for the tool
  description?: string;  // Human-readable description
  inputSchema: {         // JSON Schema for the tool's parameters
    type: "object",
    properties: { ... }  // Tool-specific parameters
  }
}
```

# Transports
Transports in the Model Context Protocol (MCP) provide the foundation for communication between clients and servers. A transport handles the underlying mechanics of how messages are sent and received.

MCP uses JSON-RPC 2.0 as its wire format. The transport layer is responsible for converting MCP protocol messages into JSON-RPC format for transmission and converting received JSON-RPC messages back into MCP protocol messages.

There are three types of JSON-RPC messages used:
### 1. Requests
```ignorelang
{
  jsonrpc: "2.0",
  id: number | string,
  method: string,
  params?: object
}
```
### 2. Responses
```ignorelang
{
  jsonrpc: "2.0",
  id: number | string,
  result?: object,
  error?: {
    code: number,
    message: string,
    data?: unknown
  }
}
```
### 3. Notifications
```ignorelang
{
  jsonrpc: "2.0",
  method: string,
  params?: object
}
```

## Built-in Transports Types
MCP includes two standard transport implementations:
### 1. Standard Input/Output (Stdio)
The stdio transport enables communication through standard input and output streams. This is particularly useful for local integrations and command-line tools.
```Python
# (Server)
    app = Server("example-server")

    async with stdio_server() as streams:
        await app.run(
            streams[0],
            streams[1],
            app.create_initialization_options()
        )
```
```Python
# (Client)
    params = StdioServerParameters(
        command="./server",
        args=["--option", "value"]
    )

    async with stdio_client(params) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
```
### 2. HTTP with Server-Sent Events (SSE)
SSE transport enables server-to-client streaming with HTTP POST requests for client-to-server communication.
```Python
# (Server)
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route

app = Server("example-server")
sse = SseServerTransport("/messages")

async def handle_sse(scope, receive, send):
    async with sse.connect_sse(scope, receive, send) as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())

async def handle_messages(scope, receive, send):
    await sse.handle_post_message(scope, receive, send)

starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)
```
```Pytho
# (Client)
async with sse_client("http://localhost:8000/sse") as streams:
    async with ClientSession(streams[0], streams[1]) as session:
        await session.initialize()
```

### Custom Transports
MCP makes it easy to implement custom transports for specific needs. Any transport implementation just needs to conform to the Transport interface:

### Error Handling
Transport implementations should handle various error scenarios:

Note that while MCP Servers are often implemented with `asyncio`, we recommend implementing low-level interfaces like transports with `anyio` for wider compatibility.
```python
    @contextmanager
    async def example_transport(scope: Scope, receive: Receive, send: Send):
        try:
            # Create streams for bidirectional communication
            read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
            write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

            async def message_handler():
                try:
                    async with read_stream_writer:
                        # Message handling logic
                        pass
                except Exception as exc:
                    logger.error(f"Failed to handle message: {exc}")
                    raise exc

            async with anyio.create_task_group() as tg:
                tg.start_soon(message_handler)
                try:
                    # Yield streams for communication
                    yield read_stream, write_stream
                except Exception as exc:
                    logger.error(f"Transport error: {exc}")
                    raise exc
                finally:
                    tg.cancel_scope.cancel()
                    await write_stream.aclose()
                    await read_stream.aclose()
        except Exception as exc:
            logger.error(f"Failed to initialize transport: {exc}")
            raise exc
```



