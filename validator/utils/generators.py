"""
This script contains custom generators for LLMs to be used with Haystack, since currently they do not support structured outputs.
(version: haystack-ai==2.8.1)
"""

# for overriding the OllamaGenerator
from typing import Any, Dict, List, Optional, Union, Callable
from haystack.dataclasses import StreamingChunk
from haystack import component
from haystack.utils import Secret
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack.components.generators import OpenAIGenerator 
from openai import Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from haystack.components.generators.openai_utils import _convert_message_to_openai_format
from haystack.dataclasses import ChatMessage, StreamingChunk


# override the current OllamaGenerator to account for structured outputs
# since haystack does not currently support this
@component
class StructuredOllamaGenerator(OllamaGenerator):
    def __init__(self,
            model: str = "orca-mini",
            url: str = "http://localhost:11434",
            generation_kwargs: Optional[Dict[str, Any]] = None,
            system_prompt: Optional[str] = None,
            template: Optional[str] = None,
            raw: bool = False,
            timeout: int = 120,
            keep_alive: Optional[Union[float, str]] = None,
            streaming_callback: Optional[Callable[[StreamingChunk], None]] = None,
            format: Optional[Dict[str, Any]] = None
        ):
        super(StructuredOllamaGenerator, self).__init__(
            model=model,
            url=url,
            generation_kwargs=generation_kwargs,
            system_prompt=system_prompt,
            template=template,
            raw=raw,
            timeout=timeout,
            keep_alive=keep_alive,
            streaming_callback=streaming_callback
        )
        self.format = format
    
    @component.output_types(replies=List[str], meta=List[Dict[str, Any]])
    def run(
        self,
        prompt: str,
        generation_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Runs an Ollama Model on the given prompt.

        :param prompt:
            The prompt to generate a response for.
        :param generation_kwargs:
            Optional arguments to pass to the Ollama generation endpoint, such as temperature,
            top_p, and others. See the available arguments in
            [Ollama docs](https://github.com/jmorganca/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values).
        :returns: A dictionary with the following keys:
            - `replies`: The responses from the model
            - `meta`: The metadata collected during the run
        """
        generation_kwargs = {**self.generation_kwargs, **(generation_kwargs or {})}

        stream = self.streaming_callback is not None

        response = self._client.generate(
            model=self.model, 
            prompt=prompt, 
            stream=stream, 
            keep_alive=self.keep_alive, 
            options=generation_kwargs,
            format=self.format
        )

        if stream:
            chunks: List[StreamingChunk] = self._handle_streaming_response(response)
            return self._convert_to_streaming_response(chunks)

        return self._convert_to_response(response)


# override the current OpenAIgenerator to account for structured outputs
# since haystack FOR SOME REASON does not currently support this (version: haystack-ai==2.8.1)
@component
class StructuredOpenAIGenerator(OpenAIGenerator):
    def __init__(self,
            api_key: Secret = Secret.from_env_var("OPENAI_API_KEY"),
            model: str = "gpt-4o-mini",
            streaming_callback: Optional[Callable[[StreamingChunk], None]] = None,
            api_base_url: Optional[str] = None,
            organization: Optional[str] = None,
            system_prompt: Optional[str] = None,
            generation_kwargs: Optional[Dict[str, Any]] = None,
            timeout: Optional[float] = None,
            max_retries: Optional[int] = None,
            response_format: Optional[Dict[str, Any]] = None
        ):
        super(StructuredOpenAIGenerator, self).__init__(
            api_key=api_key,
            model=model,
            streaming_callback=streaming_callback,
            api_base_url=api_base_url,
            organization=organization,
            system_prompt=system_prompt,
            generation_kwargs=generation_kwargs,
            timeout=timeout,
            max_retries=max_retries
        )
        self.response_format = response_format
    
    @component.output_types(replies=List[str], meta=List[Dict[str, Any]])
    def run(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        streaming_callback: Optional[Callable[[StreamingChunk], None]] = None,
        generation_kwargs: Optional[Dict[str, Any]] = None,
    ):
        """
        Invoke the text generation inference based on the provided messages and generation parameters.

        :param prompt:
            The string prompt to use for text generation.
        :param system_prompt:
            The system prompt to use for text generation. If this run time system prompt is omitted, the system
            prompt, if defined at initialisation time, is used.
        :param streaming_callback:
            A callback function that is called when a new token is received from the stream.
        :param generation_kwargs:
            Additional keyword arguments for text generation. These parameters will potentially override the parameters
            passed in the `__init__` method. For more details on the parameters supported by the OpenAI API, refer to
            the OpenAI [documentation](https://platform.openai.com/docs/api-reference/chat/create).
        :returns:
            A list of strings containing the generated responses and a list of dictionaries containing the metadata
        for each response.
        """
        message = ChatMessage.from_user(prompt)
        if system_prompt is not None:
            messages = [ChatMessage.from_system(system_prompt), message]
        elif self.system_prompt:
            messages = [ChatMessage.from_system(self.system_prompt), message]
        else:
            messages = [message]

        # update generation kwargs by merging with the generation kwargs passed to the run method
        generation_kwargs = {**self.generation_kwargs, **(generation_kwargs or {})}

        # check if streaming_callback is passed
        streaming_callback = streaming_callback or self.streaming_callback

        # adapt ChatMessage(s) to the format expected by the OpenAI API
        openai_formatted_messages = [_convert_message_to_openai_format(message) for message in messages]

        completion: Union[Stream[ChatCompletionChunk], ChatCompletion] = self.client.chat.completions.create(
            model=self.model,
            messages=openai_formatted_messages,  # type: ignore
            stream=streaming_callback is not None,
            response_format=self.response_format,
            **generation_kwargs,
        )

        completions: List[ChatMessage] = []
        if isinstance(completion, Stream):
            num_responses = generation_kwargs.pop("n", 1)
            if num_responses > 1:
                raise ValueError("Cannot stream multiple responses, please set n=1.")
            chunks: List[StreamingChunk] = []
            completion_chunk: Optional[ChatCompletionChunk] = None

            # pylint: disable=not-an-iterable
            for completion_chunk in completion:
                if completion_chunk.choices and streaming_callback:
                    chunk_delta: StreamingChunk = self._build_chunk(completion_chunk)
                    chunks.append(chunk_delta)
                    streaming_callback(chunk_delta)  # invoke callback with the chunk_delta
            # Makes type checkers happy
            assert completion_chunk is not None
            completions = [self._create_message_from_chunks(completion_chunk, chunks)]
        elif isinstance(completion, ChatCompletion):
            completions = [self._build_message(completion, choice) for choice in completion.choices]

        # before returning, do post-processing of the completions
        for response in completions:
            self._check_finish_reason(response)

        return {"replies": [message.text for message in completions], "meta": [message.meta for message in completions]}