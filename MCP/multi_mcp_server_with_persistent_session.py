"""
Keep the sessions open for both servers using client.session.
"""
from typing import List
from typing_extensions import TypedDict
from typing import Annotated
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.prompts import load_mcp_prompt
import asyncio

client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            "args": ["math_mcp_server.py"],
            "transport": "stdio",
        },
        "bmi": {
            "url": "http://localhost:8000/mcp",
            "transport": "streamable_http",
        }
    }
)


async def create_graph(math_session, bmi_session):
    """
    Two session is being passed
    :param math_session:
    :param bmi_session:
    :return:
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        api_key="your_google_api_key"
    )

    math_tools = await load_mcp_tools(math_session)
    bmi_tools = await load_mcp_tools(bmi_session)
    tools = math_tools + bmi_tools
    llm_with_tool = llm.bind_tools(tools)

    system_prompt = await load_mcp_prompt(math_session, "system_prompt")
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
    # check both session
    async with client.session("math") as math_session, client.session("bmi") as bmi_session:
        agent = await create_graph(math_session, bmi_session)
        while True:
            message = input("User: ")
            response = await agent.ainvoke({"messages": message}, config=config)
            print("AI: " + response["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())


"""
Output:

User: Hi
AI: Hi there! How can I help you today?
User: how many tools do you have
AI: I have 3 tools available: `add`, `multiply`, and `calculate_bmi`.
User: find 5 * 4
Processing request of type CallToolRequest
AI: The answer is 20.
"""