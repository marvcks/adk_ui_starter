import os
import json
import base64
from typing import Optional, TypedDict, List, Dict, Any

from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import TavilySearchResults

# Instantiate the LangChain tool
tavily_tool_instance = TavilySearchResults(
    max_results=2,
    # search_depth="advanced",
    include_answer=True,
    include_raw_content=False,
    include_images=False,
)

# Wrap it with LangchainTool for ADK
adk_tavily_tool = LangchainTool(tool=tavily_tool_instance)