import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client


# Math Server Parameters
server_params = StdioServerParameters(
    command="python",
    args=["math_mcp_server.py"],
    env=None,
)

"""
# Math server for streamable http
math_server_url = "http://localhost:8000/mcp"

# use streamablehttp_client instead of stdio_client
async def main():
    async with streamablehttp_client(math_server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
"""


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available prompts
            response = await session.list_prompts()
            print("################ Prompts ###################")
            for prompt in response.prompts:
                print(prompt)

            # List available resources
            response = await session.list_resources()
            print("################ Resources ###################")
            for resource in response.resources:
                print(resource)

            # List available resource templates
            response = await session.list_resource_templates()
            print("################ Resource Templates ###################")
            for resource_template in response.resourceTemplates:
                print(resource_template)

            # List available tools
            response = await session.list_tools()
            print("################ Tools ###################")
            for tool in response.tools:
                print(tool)

            # Get a prompt
            prompt = await session.get_prompt("example_prompt", arguments={"question": "what is 2+2"})
            print("################ Prompt ###################")
            print(prompt.messages[0].content.text)

            # Read a resource
            content, mime_type = await session.read_resource("greeting://Alice")
            print("################ Content ###################")
            print(mime_type[1][0].text)

            # Call a tool
            result = await session.call_tool("add", arguments={"a": 2, "b": 2})
            print("################ Result ###################")
            print(result.content[0].text)


if __name__ == '__main__':
    asyncio.run(main())
