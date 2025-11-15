"""
Simple chat function
"""

from langchain_core.messages import HumanMessage


async def chat(llm, message):
    """Send message to LLM, get response"""
    response = await llm.ainvoke([HumanMessage(content=message)])
    return response.content