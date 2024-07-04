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
        ctx, version=stream_version, config=config, exclude_names=["guardrails"]
    ):
        kind = event["event"]
        llm_name = event["name"]
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                # Empty content in the context of OpenAI means that the model is asking for a tool to be invoked,
                # so we only print non-empty content
                event_output += content
                output = event_transformer(content, llm_name)
                yield output
        elif kind == "on_chat_model_end":
            final_outputs.append(event_output)
            event_output = ""
        elif kind == "on_chain_end" and event["name"] == "LangGraph":
            output = event["data"]["output"]
            if isinstance(output, dict):
                ep_output = output.get("entry_point", {})
                conv_type = ep_output.get("conv_type")
                if conv_type.lower() == "failed_guard":
                    msgs = ep_output.get("messages")
                    msg_content = msgs[0].content
                    final_outputs.append(msg_content)
                    content = event_transformer(msg_content, llm_name)
                    yield content

    callback(final_outputs[-1]) if callback else None
