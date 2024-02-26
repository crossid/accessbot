from typing import Callable, Dict

from langchain.schema.runnable import Runnable


def sse_client_transformer(output: str) -> str:
    event_str = f"event: chat-message\ndata: {output}\n\n"
    return event_str


async def streaming(
    runnable: Runnable,
    ctx: Dict,
    event_transformer,
    callback: Callable[[list], None] = None,
    stream_version: str = "v1",
):
    final_output = ""
    async for event in runnable.astream_events(
        ctx,
        version=stream_version,
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # Empty content in the context of OpenAI means that the model is asking for a tool to be invoked,
                # so we only print non-empty content
                output = event_transformer(content)
                final_output += content
                yield output
    callback(final_output) if callback else None
