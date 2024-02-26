import asyncio
import time
from typing import Any, AsyncIterator, Iterator, List, Optional, Union

import tiktoken
from langchain.chat_models.fake import FakeListChatModel
from langchain.schema import BaseMessage
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import (
    agenerate_from_stream,
    generate_from_stream,
)
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk, ChatResult

FOR_MODEL = "gpt-3.5-turbo"


class FakeChatOpenAI(FakeListChatModel):
    streaming: bool = True
    encoding: tiktoken.Encoding = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.encoding is None:
            self.encoding = tiktoken.encoding_for_model(FOR_MODEL)

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Union[List[str], None] = None,
        run_manager: Union[CallbackManagerForLLMRun, None] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        encoded_tokens = self.encoding.encode(response)
        for token in encoded_tokens:
            c = self.encoding.decode_single_token_bytes(token).decode()
            if self.sleep is not None:
                time.sleep(self.sleep)
            yield ChatGenerationChunk(message=AIMessageChunk(content=c))
            if run_manager:
                run_manager.on_llm_new_token(c, chunk=c)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        stream: Optional[bool] = None,
        **kwargs: Any,
    ) -> ChatResult:
        should_stream = stream if stream is not None else self.streaming
        if should_stream:
            stream_iter = self._stream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            return generate_from_stream(stream_iter)
        message_dicts, params = self._create_message_dicts(messages, stop)
        params = {
            **params,
            **({"stream": stream} if stream is not None else {}),
            **kwargs,
        }
        response = self.completion_with_retry(
            messages=message_dicts, run_manager=run_manager, **params
        )
        return self._create_chat_result(response)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Union[List[str], None] = None,
        run_manager: Union[AsyncCallbackManagerForLLMRun, None] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        response = self.responses[self.i]
        if self.i < len(self.responses) - 1:
            self.i += 1
        else:
            self.i = 0
        encoded_tokens = self.encoding.encode(response)
        for token in encoded_tokens:
            c = self.encoding.decode_single_token_bytes(token).decode()
            if self.sleep is not None:
                await asyncio.sleep(self.sleep)
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=c))
            yield chunk
            if run_manager:
                await run_manager.on_llm_new_token(token=chunk.text, chunk=chunk)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        stream: Optional[bool] = None,
        **kwargs: Any,
    ) -> ChatResult:
        should_stream = stream if stream is not None else self.streaming
        if should_stream:
            stream_iter = self._astream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            return await agenerate_from_stream(stream_iter)

        message_dicts, params = self._create_message_dicts(messages, stop)
        params = {
            **params,
            **({"stream": stream} if stream is not None else {}),
            **kwargs,
        }
        # response = await acompletion_with_retry(
        #     self, messages=message_dicts, run_manager=run_manager, **params
        # )
        response = "TODO"
        return self._create_chat_result(response)
