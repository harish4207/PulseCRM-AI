from langchain_core.messages import HumanMessage, ToolMessage

from app.ai.graph import agent

# User asks a question
messages = [
    HumanMessage(content="Find doctor Sharma")
]

# First LLM response
ai_response = agent.invoke(messages)

print("AI Response:")
print(ai_response)
print()

# Did AI request a tool?
if ai_response.tool_calls:

    tool_call = ai_response.tool_calls[0]

    print("Tool Requested:")
    print(tool_call)
    print()

    if tool_call["name"] == "search_hcp":

        from app.ai.tools import search_hcp

        tool_result = search_hcp.invoke(tool_call["args"])

        print("Tool Result:")
        print(tool_result)
        print()

        messages.append(ai_response)

        messages.append(
            ToolMessage(
                content=tool_result,
                tool_call_id=tool_call["id"]
            )
        )

        final_response = agent.invoke(messages)

        print("Final AI Response:")
        print(final_response.content)