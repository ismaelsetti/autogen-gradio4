import os
import sys
import threading
from itertools import chain

import anyio
import autogen
import gradio as gr
from autogen import Agent, AssistantAgent, OpenAIWrapper, UserProxyAgent
from autogen.code_utils import extract_code
from gradio import ChatInterface, Request
from gradio.helpers import special_args

LOG_LEVEL = "INFO"
TIMEOUT = 1000


class myChatInterface(ChatInterface):
    async def _submit_fn(
        self,
        message: str,
        history_with_input: list[list[str | None]],
        request: Request,
        *args,
    ) -> tuple[list[list[str | None]], list[list[str | None]]]:
        history = history_with_input[:-1]
        inputs, _, _ = special_args(self.fn, inputs=[message, history, *args], request=request)

        if self.is_async:
            await self.fn(*inputs)
        else:
            await anyio.to_thread.run_sync(self.fn, *inputs, limiter=self.limiter)

        # history.append([message, response])
        return history, history


with gr.Blocks() as demo:

    def _is_termination_msg(message):
        """Check if a message is a termination message.
        Terminate when no code block is detected. Currently only detect python code blocks.
        """
        if isinstance(message, dict):
            message = message.get("content")
            if message is None:
                return False
        cb = extract_code(message)
        contain_code = False
        for c in cb:
            # todo: support more languages
            if c[0] == "python":
                contain_code = True
                break
        return not contain_code

    def initialize_agents(config_list):
        assistant = AssistantAgent(
            name="assistant",
            max_consecutive_auto_reply=5,
            llm_config={
                # "seed": 42,
                "timeout": TIMEOUT,
                "config_list": config_list,
            },
        )

        userproxy = UserProxyAgent(
            name="userproxy",
            human_input_mode="NEVER",
            is_termination_msg=_is_termination_msg,
            max_consecutive_auto_reply=5,
            # code_execution_config=False,
            code_execution_config={
                "work_dir": "coding",
                "use_docker": False,  # set to True or image name like "python:3" to use docker
            },
        )

        return assistant, userproxy

    def chat_to_oai_message(chat_history):
        """Convert chat history to OpenAI message format."""
        messages = []
        if LOG_LEVEL == "DEBUG":
            print(f"chat_to_oai_message: {chat_history}")
        for msg in chat_history:
            messages.append(
                {
                    "content": msg[0].split()[0] if msg[0].startswith("exitcode") else msg[0],
                    "role": "user",
                }
            )
            messages.append({"content": msg[1], "role": "assistant"})
        return messages

    def oai_message_to_chat(oai_messages, sender):
        """Convert OpenAI message format to chat history."""
        chat_history = []
        messages = oai_messages[sender]
        if LOG_LEVEL == "DEBUG":
            print(f"oai_message_to_chat: {messages}")
        for i in range(0, len(messages), 2):
            chat_history.append(
                [
                    messages[i]["content"],
                    messages[i + 1]["content"] if i + 1 < len(messages) else "",
                ]
            )
        return chat_history

    def initiate_chat(user_message, chat_history):
        if LOG_LEVEL == "DEBUG":
            print(f"chat_history_init: {chat_history}")

        assistant.reset()
        oai_messages = chat_to_oai_message(chat_history)
        assistant._oai_system_message_origin = assistant._oai_system_message.copy()
        assistant._oai_system_message += oai_messages

        try:
            userproxy.initiate_chat(assistant, message=user_message)
            messages = userproxy.chat_messages
            chat_history += oai_message_to_chat(messages, assistant)

        except Exception as e:
            # agent_history += [user_message, str(e)]
            chat_history.append([user_message, str(e)])

        assistant._oai_system_message = assistant._oai_system_message_origin.copy()
        if LOG_LEVEL == "DEBUG":
            print(f"chat_history: {chat_history}")
            # print(f"agent_history: {agent_history}")
        return chat_history

    def chatbot_reply(input_text, chat_history):
        """Chat with the agent through terminal."""
        try:
            messages = initiate_chat(input_text, chat_history)
        except Exception as e:
            messages = [
                [
                    input_text,
                    str(e) if len(str(e)) > 0 else "Invalid Request to OpenAI, please check your API keys.",
                ]
            ]
        return messages

    def get_description_text():
        return """
        # Microsoft AutoGen: Multi-Round Human Interaction Chatbot Demo

        This demo shows how to build a chatbot which can handle multi-round conversations with human interactions.
        """

    def respond(message, chat_history):
        chat_history[:] = chatbot_reply(message, chat_history)
        if LOG_LEVEL == "DEBUG":
            print(f"return chat_history: {chat_history}")
        return ""

    config_list, assistant, userproxy = (
        [
            {
                "model": "llama3",
                "base_url": "http://localhost:11434/v1",
                "api_key": "ollama",
            }
        ],
        None,
        None,
    )
    assistant, userproxy = initialize_agents(config_list)

    description = gr.Markdown(get_description_text())

    chatbot = gr.Chatbot(
        [],
        elem_id="chatbot",
        bubble_full_width=False,
        avatar_images=(
            "human.png",
            (os.path.join(os.path.dirname(__file__), "autogen.png")),
        ),
        render=False,
        height=600,
    )

    txt_input = gr.Textbox(
        scale=4,
        show_label=False,
        placeholder="Enter text and press enter",
        container=False,
        render=False,
        autofocus=True,
    )

    chatiface = myChatInterface(
        respond,
        chatbot=chatbot,
        textbox=txt_input,
        examples=[
            ["write a python function to count the sum of two numbers?"],
            ["what if the production of two numbers?"],
            [
                "Plot a chart of the last year's stock prices of Microsoft, Google and Apple and save to stock_price.png."
            ]
        ],
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=5)
    demo.launch(share=True, server_name="0.0.0.0")
