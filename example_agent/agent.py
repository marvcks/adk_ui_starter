import os
import asyncio

from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from google.adk.tools import FunctionTool
from typing import Any, Dict


toolset = MCPToolset(
    connection_params=SseServerParams(
        url="https://qc-database-uuid1761896309.app-space.dplink.cc/sse?token=b05e582ae1324acdbbb40ac2b84209ef",
    ),
)

model = LiteLlm(
    model=os.getenv("MODEL_NAME"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_base=os.getenv("OPENAI_BASE_URL"),
    )

# Create agent
root_agent = Agent(
    name="QA_Agent",
    model=model,
    instruction="You are an assistant by using tools to answer questions.",
    tools=[toolset]
)
