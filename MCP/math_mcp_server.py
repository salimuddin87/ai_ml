from mcp.server.fastmcp import FastMCP

# Create a server name "Math"
mcp = FastMCP("Math")


# Prompts
@mcp.prompt()
def example_prompt(question: str) -> str:
    """ For math Questions """
    return f"""
    You are a math assistant. Answer the question.
    """


@mcp.prompt()
def system_prompt() -> str:
    """ For General Instructions """
    return f"""
    You are AI assistant use Tools to answer.
    """


# Resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """ Dynamic resource """
    return f"Hello, {name}!"


@mcp.resource("config://app")
def get_config() -> str:
    """ Static Resource """
    return f"App configuration Here!"


# Tools
@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    return a * b


if __name__ == '__main__':
    mcp.run()  # To run server
    # mcp.run(transport="streamable-http")  # Run server via streamable http
