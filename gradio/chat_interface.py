"""
This file defines a useful high-level abstraction to build Gradio chatbots: ChatInterface.
"""


from __future__ import annotations

import inspect
import warnings
from typing import Callable, Generator

from gradio_client.documentation import document, set_documentation_group

from gradio.blocks import Blocks
from gradio.components import (
    Button,
    Chatbot,
    Markdown,
    State,
    Textbox,
)
from gradio.events import Dependency, EventListenerMethod
from gradio.helpers import create_examples as Examples  # noqa: N812
from gradio.layouts import Column, Group, Row
from gradio.themes import ThemeClass as Theme

set_documentation_group("chatinterface")


@document()
class ChatInterface(Blocks):
    """
    ChatInterface is Gradio's high-level abstraction for creating chatbot UIs, and allows you to create
    a web-based demo around a chatbot model in a few lines of code. Only one parameter is required: fn, which
    takes a function that governs the response of the chatbot based on the user input and chat history. Additional
    parameters can be used to control the appearance and behavior of the demo.

    Example:
        import gradio as gr

        def echo(message, history):
            return message

        demo = gr.ChatInterface(fn=echo, examples=["hello", "hola", "merhaba"], title="Echo Bot")
        demo.launch()
    Demos: chatinterface_random_response, chatinterface_streaming_echo
    Guides: creating-a-chatbot-fast, sharing-your-app
    """

    def __init__(
        self,
        fn: Callable,
        *,
        chatbot: Chatbot | None = None,
        textbox: Textbox | None = None,
        examples: list[str] | None = None,
        cache_examples: bool | None = None,
        title: str | None = None,
        description: str | None = None,
        theme: Theme | str | None = None,
        css: str | None = None,
        analytics_enabled: bool | None = None,
        submit_btn: str | None | Button = "Submit",
        stop_btn: str | None | Button = "Stop",
        retry_btn: str | None | Button = "🔄  Retry",
        undo_btn: str | None | Button = "↩️ Undo",
        clear_btn: str | None | Button = "🗑️  Clear",
    ):
        """
        Parameters:
            fn: the function to wrap the chat interface around. Should accept two parameters: a string input message and list of two-element lists of the form [[user_message, bot_message], ...] representing the chat history, and return a string response. See the Chatbot documentation for more information on the chat history format.
            chatbot: an instance of the gr.Chatbot component to use for the chat interface, if you would like to customize the chatbot properties. If not provided, a default gr.Chatbot component will be created.
            textbox: an instance of the gr.Textbox component to use for the chat interface, if you would like to customize the textbox properties. If not provided, a default gr.Textbox component will be created.
            examples: sample inputs for the function; if provided, appear below the chatbot and can be clicked to populate the chatbot input.
            cache_examples: If True, caches examples in the server for fast runtime in examples. The default option in HuggingFace Spaces is True. The default option elsewhere is False.
            title: a title for the interface; if provided, appears above chatbot in large font. Also used as the tab title when opened in a browser window.
            description: a description for the interface; if provided, appears above the chatbot and beneath the title in regular font. Accepts Markdown and HTML content.
            theme: Theme to use, loaded from gradio.themes.
            css: custom css or path to custom css file to use with interface.
            analytics_enabled: Whether to allow basic telemetry. If None, will use GRADIO_ANALYTICS_ENABLED environment variable if defined, or default to True.
            submit_btn: Text to display on the submit button. If None, no button will be displayed. If a Button object, that button will be used.
            stop_btn: Text to display on the stop button, which replaces the submit_btn when the submit_btn or retry_btn is clicked and response is streaming. Clicking on the stop_btn will halt the chatbot response. If set to None, stop button functionality does not appear in the chatbot. If a Button object, that button will be used as the stop button.
            retry_btn: Text to display on the retry button. If None, no button will be displayed. If a Button object, that button will be used.
            undo_btn: Text to display on the delete last button. If None, no button will be displayed. If a Button object, that button will be used.
            clear_btn: Text to display on the clear button. If None, no button will be displayed. If a Button object, that button will be used.
        """
        super().__init__(
            analytics_enabled=analytics_enabled,
            mode="chat_interface",
            css=css,
            title=title or "Gradio",
            theme=theme,
        )
        if len(inspect.signature(fn).parameters) != 2:
            warnings.warn(
                "The function to ChatInterface should take two inputs (message, history) and return a single string response.",
                UserWarning,
            )

        self.fn = fn
        self.is_generator = inspect.isgeneratorfunction(self.fn)
        self.examples = examples
        if self.space_id and cache_examples is None:
            self.cache_examples = True
        else:
            self.cache_examples = cache_examples or False
        self.buttons: list[Button] = []

        with self:
            if title:
                Markdown(
                    f"<h1 style='text-align: center; margin-bottom: 1rem'>{self.title}</h1>"
                )
            if description:
                Markdown(description)

            with Column(variant="panel"):
                if chatbot:
                    self.chatbot = chatbot.render()
                else:
                    self.chatbot = Chatbot(label="Chatbot")

                with Group():
                    with Row():
                        if textbox:
                            textbox.container = False
                            textbox.show_label = False
                            self.textbox = textbox.render()
                        else:
                            self.textbox = Textbox(
                                container=False,
                                show_label=False,
                                placeholder="Type a message...",
                                scale=7,
                                autofocus=True,
                            )
                        if submit_btn:
                            if isinstance(submit_btn, Button):
                                submit_btn.render()
                            elif isinstance(submit_btn, str):
                                submit_btn = Button(
                                    submit_btn,
                                    variant="primary",
                                    scale=1,
                                    min_width=150,
                                )
                            else:
                                raise ValueError(
                                    f"The submit_btn parameter must be a gr.Button, string, or None, not {type(submit_btn)}"
                                )
                        if stop_btn:
                            if isinstance(stop_btn, Button):
                                stop_btn.visible = False
                                stop_btn.render()
                            elif isinstance(stop_btn, str):
                                stop_btn = Button(
                                    stop_btn,
                                    variant="stop",
                                    visible=False,
                                    scale=1,
                                    min_width=150,
                                )
                            else:
                                raise ValueError(
                                    f"The stop_btn parameter must be a gr.Button, string, or None, not {type(stop_btn)}"
                                )
                        self.buttons.extend([submit_btn, stop_btn])

                with Row():
                    for btn in [retry_btn, undo_btn, clear_btn]:
                        if btn:
                            if isinstance(btn, Button):
                                btn.render()
                            elif isinstance(btn, str):
                                btn = Button(btn, variant="secondary")
                            else:
                                raise ValueError(
                                    f"All the _btn parameters must be a gr.Button, string, or None, not {type(btn)}"
                                )
                        self.buttons.append(btn)

                    self.fake_api_btn = Button("Fake API", visible=False)
                    self.fake_response_textbox = Textbox(
                        label="Response", visible=False
                    )
                    (
                        self.submit_btn,
                        self.stop_btn,
                        self.retry_btn,
                        self.undo_btn,
                        self.clear_btn,
                    ) = self.buttons

            if examples:
                if self.is_generator:
                    examples_fn = self._examples_stream_fn
                else:
                    examples_fn = self._examples_fn

                self.examples_handler = Examples(
                    examples=examples,
                    inputs=self.textbox,
                    outputs=self.chatbot,
                    fn=examples_fn,
                    cache_examples=self.cache_examples,
                )

            self.saved_input = State()
            self.chatbot_state = State([])

            self._setup_events()
            self._setup_api()

    def _setup_events(self) -> None:
        submit_fn = self._stream_fn if self.is_generator else self._submit_fn
        submit_event = (
            self.textbox.submit(
                self._clear_and_save_textbox,
                [self.textbox],
                [self.textbox, self.saved_input],
                api_name=False,
                queue=False,
            )
            .then(
                self._display_input,
                [self.saved_input, self.chatbot_state],
                [self.chatbot, self.chatbot_state],
                api_name=False,
                queue=False,
            )
            .then(
                submit_fn,
                [self.saved_input, self.chatbot_state],
                [self.chatbot, self.chatbot_state],
                api_name=False,
            )
        )
        self._setup_stop_events(self.textbox.submit, submit_event)

        if self.submit_btn:
            click_event = (
                self.submit_btn.click(
                    self._clear_and_save_textbox,
                    [self.textbox],
                    [self.textbox, self.saved_input],
                    api_name=False,
                    queue=False,
                )
                .then(
                    self._display_input,
                    [self.saved_input, self.chatbot_state],
                    [self.chatbot, self.chatbot_state],
                    api_name=False,
                    queue=False,
                )
                .then(
                    submit_fn,
                    [self.saved_input, self.chatbot_state],
                    [self.chatbot, self.chatbot_state],
                    api_name=False,
                )
            )
            self._setup_stop_events(self.submit_btn.click, click_event)

        if self.retry_btn:
            retry_event = (
                self.retry_btn.click(
                    self._delete_prev_fn,
                    [self.chatbot_state],
                    [self.chatbot, self.saved_input, self.chatbot_state],
                    api_name=False,
                    queue=False,
                )
                .then(
                    self._display_input,
                    [self.saved_input, self.chatbot_state],
                    [self.chatbot, self.chatbot_state],
                    api_name=False,
                    queue=False,
                )
                .then(
                    submit_fn,
                    [self.saved_input, self.chatbot_state],
                    [self.chatbot, self.chatbot_state],
                    api_name=False,
                )
            )
            self._setup_stop_events(self.retry_btn.click, retry_event)

        if self.undo_btn:
            self.undo_btn.click(
                self._delete_prev_fn,
                [self.chatbot_state],
                [self.chatbot, self.saved_input, self.chatbot_state],
                api_name=False,
                queue=False,
            ).then(
                lambda x: x,
                [self.saved_input],
                [self.textbox],
                api_name=False,
                queue=False,
            )

        if self.clear_btn:
            self.clear_btn.click(
                lambda: ([], [], None),
                None,
                [self.chatbot, self.chatbot_state, self.saved_input],
                queue=False,
                api_name=False,
            )

    def _setup_stop_events(
        self, event_trigger: EventListenerMethod, event_to_cancel: Dependency
    ) -> None:
        if self.stop_btn and self.is_generator:
            if self.submit_btn:
                event_trigger(
                    lambda: (Button.update(visible=False), Button.update(visible=True)),
                    None,
                    [self.submit_btn, self.stop_btn],
                    api_name=False,
                    queue=False,
                )
                event_to_cancel.then(
                    lambda: (Button.update(visible=True), Button.update(visible=False)),
                    None,
                    [self.submit_btn, self.stop_btn],
                    api_name=False,
                    queue=False,
                )
            else:
                event_trigger(
                    lambda: Button.update(visible=True),
                    None,
                    [self.stop_btn],
                    api_name=False,
                    queue=False,
                )
                event_to_cancel.then(
                    lambda: Button.update(visible=False),
                    None,
                    [self.stop_btn],
                    api_name=False,
                    queue=False,
                )
            self.stop_btn.click(
                None,
                None,
                None,
                cancels=event_to_cancel,
                api_name=False,
            )

    def _setup_api(self) -> None:
        api_fn = self._api_stream_fn if self.is_generator else self._api_submit_fn

        self.fake_api_btn.click(
            api_fn,
            [self.textbox, self.chatbot_state],
            [self.textbox, self.chatbot_state],
            api_name="chat",
        )

    def _clear_and_save_textbox(self, message: str) -> tuple[str, str]:
        return "", message

    def _display_input(
        self, message: str, history: list[list[str | None]]
    ) -> tuple[list[list[str | None]], list[list[str | None]]]:
        history.append([message, None])
        return history, history

    def _submit_fn(
        self, message: str, history_with_input: list[list[str | None]]
    ) -> tuple[list[list[str | None]], list[list[str | None]]]:
        history = history_with_input[:-1]
        response = self.fn(message, history)
        history.append([message, response])
        return history, history

    def _stream_fn(
        self, message: str, history_with_input: list[list[str | None]]
    ) -> Generator[tuple[list[list[str | None]], list[list[str | None]]], None, None]:
        history = history_with_input[:-1]
        generator = self.fn(message, history)
        try:
            first_response = next(generator)
            update = history + [[message, first_response]]
            yield update, update
        except StopIteration:
            update = history + [[message, None]]
            yield update, update
        for response in generator:
            update = history + [[message, response]]
            yield update, update

    def _api_submit_fn(
        self, message: str, history: list[list[str | None]]
    ) -> tuple[str, list[list[str | None]]]:
        response = self.fn(message, history)
        history.append([message, response])
        return response, history

    def _api_stream_fn(
        self, message: str, history: list[list[str | None]]
    ) -> Generator[tuple[str | None, list[list[str | None]]], None, None]:
        generator = self.fn(message, history)
        try:
            first_response = next(generator)
            yield first_response, history + [[message, first_response]]
        except StopIteration:
            yield None, history + [[message, None]]
        for response in generator:
            yield response, history + [[message, response]]

    def _examples_fn(self, message: str) -> list[list[str | None]]:
        return [[message, self.fn(message, [])]]

    def _examples_stream_fn(
        self, message: str
    ) -> Generator[list[list[str | None]], None, None]:
        for response in self.fn(message, []):
            yield [[message, response]]

    def _delete_prev_fn(
        self, history: list[list[str | None]]
    ) -> tuple[list[list[str | None]], str, list[list[str | None]]]:
        try:
            message, _ = history.pop()
        except IndexError:
            message = ""
        return history, message or "", history
