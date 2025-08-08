"""
Integrate the MCP client with LangGraph to create an AI agent
"""
from typing import Annotated, List
from typing_extensions import TypedDict

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver

from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.prompts import load_mcp_prompt
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import asyncio


# Math Server parameters
server_params = StdioServerParameters(
    command="python",
    args=["math_mcp_server.py"],
    env=None,
)


async def create_graph(session):
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        api_key="your_google_api_key",
    )

    tools = await load_mcp_tools(session)
    llm_with_tool = llm.bind_tools(tools)

    system_prompt = await load_mcp_prompt(session, "system_prompt")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt[0].content),
        MessagesPlaceholder("messages")
    ])
    chat_llm = prompt_template | llm_with_tool

    # State Management
    class State(TypedDict):
        messages: Annotated[List[AnyMessage], add_messages]

    # Nodes
    def chat_node(state: State) -> State:
        state["messages"] = chat_llm.invoke({"messages": state["messages"]})
        return state

    # Building the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_node("tool_node", ToolNode(tools=tools))

    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_conditional_edges("chat_node", tools_condition, {"tools": "tool_node", "__end__": END})
    graph_builder.add_edge("tool_node", "chat_node")

    graph = graph_builder.compile(checkpointer=MemorySaver())
    return graph


async def main():
    config = {"configurable": {"thread_id": 1234}}
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Check available tools
            tools = await load_mcp_tools(session)
            print("Available tools: ", [tool.name for tool in tools])

            # check available prompts
            prompts = await load_mcp_prompt(session, "example_prompt", arguments={"question": "what is 2+2"})
            print("Available prompts: ", [prompt.content for prompt in prompts])

            prompts = await load_mcp_prompt(session, "system_prompt")
            print("Available prompts: ", [prompt.content for prompt in prompts])

            # check available resources
            resources = await load_mcp_resources(session, uris=["greeting://Alice", "config://app"])
            print("Available resources: ", [resource.data for resource in resources])

            # Use the MCP Server in the graph
            agent = await create_graph(session)
            while True:
                message = input("User: ")
                response = await agent.ainvoke({"messages": message}, config=config)
                print("AI: "+response["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())


"""
Processing request of type ListToolsRequest
Available tools: ['add', 'multiply']

Processing request of type GetPromptRequest
Available prompts: ['\n    You are a math assistant. Answer the question.\n    Question: what is 2+2\n    ']

Processing request of type GetPromptRequest
Available prompts: ['\n    You are an AI assistant use the tools if needed.\n    ']

Processing request of type ReadResourceRequest
Processing request of type ReadResourceRequest
Available resources: ['Hello, Alice!', 'App configuration here']

Processing request of type ListToolsRequest
Processing request of type GetPromptRequest

User: Hi
AI: Hi there! How can I help you today?
User: what is 2 + 4
Processing request of type CallToolRequest
AI: 2 + 4 = 6
"""