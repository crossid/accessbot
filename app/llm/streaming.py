from typing import Callable, Dict

from langchain.schema.runnable import Runnable, RunnableConfig


async def streaming(
    runnable: Runnable,
    config: RunnableConfig,
    ctx: Dict,
    event_transformer,
    callback: Callable[[list], None] = None,
    stream_version: str = "v1",
):
    final_outputs = []
    event_output = ""
    async for event in runnable.astream_events(
        ctx, version=stream_version, config=config
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # Empty content in the context of OpenAI means that the model is asking for a tool to be invoked,
                # so we only print non-empty content
                event_output += content
                llm_name = event["name"]
                output = event_transformer(content, llm_name)
                yield output
        elif kind == "on_chat_model_end":
            final_outputs.append(event_output)
            event_output = ""

    callback(final_outputs[-1]) if callback else None
