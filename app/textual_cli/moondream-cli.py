from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
    ScrollableContainer,
    VerticalGroup,
)
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Select,
    Label,
    RichLog,
    Input,
)
from textual.screen import Screen
from textual.message import Message

from cli import HypervisorCLI


class KeyLogger(RichLog):
    def on_key(self, event: events.Key) -> None:
        self.write(event)


class CaptionInput(Static):
    def compose(self):
        yield Input(placeholder="Image Path", id="image_path_field")


class QueryInput(Static):
    def compose(self):
        yield Input(placeholder="Image Path", id="image_path_field")
        yield Input(placeholder="Prompt", id="prompt_field")


class DetectInput(Static):
    def compose(self):
        yield Input(placeholder="Image Path", id="image_path_field")
        yield Input(placeholder="Detect", id="prompt_field")


class PointInput(Static):
    def compose(self):
        yield Input(placeholder="Image Path", id="image_path_field")
        yield Input(placeholder="Point", id="prompt_field")


class Infer(Static):
    def compose(self) -> ComposeResult:
        with Horizontal(
            id="capibility_horizontal_group",
        ):
            yield Button("Caption", id="caption_button", variant="primary")
            yield Button("Query", id="query_button")
            yield Button("Detect", id="detect_button")
            yield Button("Point", id="point_button")
        with Container(id="capibility_input_container", classes="bottom"):
            yield Horizontal(CaptionInput())

    @on(Button.Pressed, "#caption_button")
    def handle_caption_button(self, event: Button.Pressed) -> None:
        self.query_one("#caption_button").variant = "primary"
        self.query_one("#query_button").variant = "default"
        self.query_one("#detect_button").variant = "default"
        self.query_one("#point_button").variant = "default"

        # Replace the content in the input container
        input_container = self.query_one("#capibility_input_container")
        input_container.remove_children()
        input_container.mount(CaptionInput())

    @on(Button.Pressed, "#query_button")
    def handle_query_button(self, event: Button.Pressed) -> None:
        self.query_one("#caption_button").variant = "default"
        self.query_one("#query_button").variant = "primary"
        self.query_one("#detect_button").variant = "default"
        self.query_one("#point_button").variant = "default"

        # Replace the content in the input container
        input_container = self.query_one("#capibility_input_container")
        input_container.remove_children()
        input_container.mount(QueryInput())

    @on(Button.Pressed, "#detect_button")
    def handle_detect_button(self, event: Button.Pressed) -> None:
        self.query_one("#caption_button").variant = "default"
        self.query_one("#query_button").variant = "default"
        self.query_one("#detect_button").variant = "primary"
        self.query_one("#point_button").variant = "default"

        # Replace the content in the input container
        input_container = self.query_one("#capibility_input_container")
        input_container.remove_children()
        input_container.mount(DetectInput())

    @on(Button.Pressed, "#point_button")
    def handle_point_button(self, event: Button.Pressed) -> None:
        self.query_one("#query_button").variant = "default"
        self.query_one("#caption_button").variant = "default"
        self.query_one("#detect_button").variant = "default"
        self.query_one("#point_button").variant = "primary"

        # Replace the content in the input container
        input_container = self.query_one("#capibility_input_container")
        input_container.remove_children()
        input_container.mount(PointInput())


class MainPannel(Static):
    def compose(self):
        with Vertical(id="infer_vertical_section"):
            yield Infer(id="infer_panel")


class MoondreamCLI(App):
    CSS_PATH = "moondream-cli.tcss"
    TITLE = "Moondream Station"

    def compose(self):
        yield Header()

        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Button("💬 Infer", id="infer_button")
                yield Button("🗄️  Logs", id="logs_button")
                yield Button("⚙️  Setting", id="setting_button")
            yield MainPannel(id="main_panel")


if __name__ == "__main__":
    app = MoondreamCLI()
    app.run()
