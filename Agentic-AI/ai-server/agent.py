
import json
import httpx

from tools import TOOL_SCHEMAS, run_tool

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"

MODEL = "qwen2.5:3b"

MAX_STEPS = 4

SYSTEM_PROMPT = (
    "You are a helpful research assistant. "
    "Use web_search for current or factual questions. "
    "Use fetch_page only if search snippets are not enough. "
    "Use calculator for math. "
    "When you use search results, cite them like [1], [2] "
    "using the numbers given. "
    "If no tool is needed, answer directly. Be concise."
)


async def run_agent(user_messages: list) -> dict:

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + user_messages

    sources = []
    steps = []

    async with httpx.AsyncClient(timeout=None) as client:

        for _ in range(MAX_STEPS):

            r = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "messages": messages,
                    "tools": TOOL_SCHEMAS
                }
            )

            r.raise_for_status()

            msg = r.json()["choices"][0]["message"]

            tool_calls = msg.get("tool_calls")

            if not tool_calls:

                return {
                    "answer": msg.get("content", ""),
                    "sources": sources,
                    "steps": steps
                }

            messages.append(msg)

            for call in tool_calls:

                name = call["function"]["name"]

                args = call["function"]["arguments"]

                if isinstance(args, str):

                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                result = await run_tool(
                    name,
                    args,
                    sources
                )

                steps.append({
                    "tool": name,
                    "args": args
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": result
                })

        messages.append({
            "role": "user",
            "content": (
                "Now give your final answer using what you found, "
                "with citations."
            )
        })

        r = await client.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages
            }
        )

        r.raise_for_status()

        answer = r.json()["choices"][0]["message"].get(
            "content", ""
        )

        return {
            "answer": answer,
            "sources": sources,
            "steps": steps
        }
