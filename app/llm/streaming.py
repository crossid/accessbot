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
    current_llm_name = None
    async for event in runnable.astream_events(
        ctx, version=stream_version, config=config
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # Empty content in the context of OpenAI means that the model is asking for a tool to be invoked,
                # so we only print non-empty content
                llm_name = event["name"]
                # initialize first llm_name
                if current_llm_name is None:
                    current_llm_name = llm_name

                output = event_transformer(content, llm_name)

                # add content from different llms to outputs in order to send only the last msg to callback
                if llm_name != current_llm_name:
                    final_outputs.append(event_output)
                    event_output = ""
                    current_llm_name = llm_name

                event_output += content
                yield output

    callback(final_outputs[-1]) if callback else None
