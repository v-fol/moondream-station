import sys
import shlex

try:
    import readline
except ImportError:
    readline = None

from typing import Dict, Callable
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

from .core.config import ConfigManager
from .core.models import ModelManager
from .core.updater import UpdateChecker
from .core.service import ServiceManager
from .core.manifest import ManifestManager
from .core.analytics import Analytics
from .ui.display import Display
from .ui.prompts import Prompts
from .completion import TabCompleter
from .session import SessionState
from .commands import CommandHandlers
from .inference import InferenceHandler
from .session_manager import SessionManager


class REPLSession:
    def __init__(self, manifest_source: str = None):
        self.console = Console()
        self.manifest_source = manifest_source
        self.config = ConfigManager()
        self.manifest_manager = ManifestManager(self.config)
        self.analytics = Analytics(self.config, self.manifest_manager)
        self.models = ModelManager(self.config, self.manifest_manager)
        self.updater = UpdateChecker(self.config, self.manifest_manager)
        self.display = Display()
        self.prompts = Prompts()
        self.session_state = SessionState()
        self.service = ServiceManager(
            self.config, self.manifest_manager, self.session_state, self.analytics
        )
        self.running = True

        # Initialize handlers
        self.commands = CommandHandlers(self)
        self.inference = InferenceHandler(self)
        self.session_manager = SessionManager(self)

        # Command mappings
        self.command_map = self._init_commands()

        # Initialize tab completer after command_map is ready
        self.completer = TabCompleter(self)

        # Load manifest first to get welcome message
        welcome_text = None
        if manifest_source:
            self._load_manifest(manifest_source)
            # Reinitialize analytics now that manifest is loaded
            self.analytics._initialize_posthog()
            messages = self.manifest_manager.get_messages()
            welcome_text = messages.get("welcome")

        # Show banner with welcome message if available
        self.display.show_banner(welcome_text)

    def _init_commands(self) -> Dict[str, Callable]:
        """Initialize command mappings"""
        return {
            "models": self.commands.models,
            "start": self.commands.start,
            "stop": self.commands.stop,
            "restart": self.commands.restart,
            "update": self.commands.update,
            "infer": self.inference.infer,
            "inference": self.inference.inference_mode,
            "help": self.commands.help,
            "ls": self.commands.help,
            "exit": self._exit,
            "quit": self._exit,
            "clear": self.commands.clear,
            "history": self.commands.history,
            "session": self.session_manager.session,
            "settings": self.commands.settings,
            "reset": self.commands.reset,
            "manual": self.commands.manual,
            "man": self.commands.manual,
        }

    def _load_manifest(self, source: str):
        """Load manifest from source"""
        try:
            with self.display.spinner(f"Loading manifest from {source}"):
                self.manifest_manager.load_manifest(
                    source, self.analytics, self.display
                )

            self.config.set("last_manifest_source", source)

            # Welcome message will be displayed in startup info instead

            # self.display.success(f"Manifest loaded successfully from {source}")

            # Auto-switch to default model if no model is selected
            self._auto_switch_default_model()

            # Check if service should auto start after manifest is loaded
            self._check_auto_start()
        except Exception as e:
            self.display.error(f"Failed to load manifest: {str(e)}")

    def _check_auto_start(self):
        """Check if service should auto start and start it if needed"""
        if self.config.get("auto_start", True) and not self.service.is_running():
            # Use available default model from manifest, not config
            model_name = self.manifest_manager.get_available_default_model()
            if model_name:
                self.analytics.track(
                    "auto_start_attempt",
                    {"model": model_name, "source": "manifest_default"},
                )
                try:
                    service_port = self.config.get("service_port", 2020)
                    with self.display.spinner(f"Preparing {model_name}"):
                        result = self.service.start(model_name, service_port)

                    if result:
                        # Set the model in config since service started successfully
                        self.config.set("current_model", model_name)
                        self.analytics.track(
                            "auto_start_success",
                            {"model": model_name, "port": service_port},
                        )
                    else:
                        self.analytics.track_error(
                            "AutoStartError",
                            "Service start returned False",
                            "auto_start_service_failed",
                        )
                        self.display.error("Failed to start inference service")
                except Exception as e:
                    self.analytics.track_error(
                        type(e).__name__, str(e), "auto_start_service_exception"
                    )
                    self.display.error(f"Failed to auto-start service: {str(e)}")
            else:
                self.analytics.track(
                    "auto_start_no_model", {"reason": "no_available_default_model"}
                )

    def _auto_switch_default_model(self):
        """Auto-switch to default model if no current model is set"""
        current_model = self.config.get("current_model")
        if not current_model:
            default_model = self.manifest_manager.get_available_default_model()
            if default_model:
                if self.models.switch_model(default_model, self.display):
                    self.display.success(f"Loaded default model: {default_model}")

    def start(self):
        """Start the REPL session"""
        # Track application launch
        self.analytics.track("app_launch", {"manifest_source": self.manifest_source})

        # self.display.show_banner()
        self._show_startup_info()

        # Check if service should auto-start
        self._check_auto_start()

        while self.running:
            try:
                self._handle_input()
            except KeyboardInterrupt:
                self._exit([])
            except EOFError:
                # Ctrl-D just prints a newline and continues
                rprint()
                continue

    def _show_startup_info(self):
        """Show startup information"""
        current_model = self.models.get_active_model()
        service_status = "🟢 Running" if self.service.is_running() else "🔴 Stopped"

        info = []
        info.append(
            f"[bold]Current Model:[/bold] {current_model.name if current_model else '[dim]None selected[/dim]'}"
        )
        info.append(f"[bold]Service:[/bold] {service_status}")

        if self.service.is_running():
            port = self.config.get("service_port", 2020)
            info.append(
                f"[bold]API Endpoint:[/bold] http://localhost:[bold green]{port}[/bold green]/v1"
            )

        info.append(
            f"[bold]Type[/bold] [cyan]help[/cyan] [bold]for available commands[/bold]"
        )

        panel = Panel(
            "\n".join(info), title="[bold blue]Status", border_style="blue", width=70
        )
        self.console.print(panel)
        self.console.print()

        # Check for updates and show warning if available
        self._check_update_warning()

        # Show manifest messages (welcome and warning)
        self._show_manifest_messages()

        # Show version-specific messages
        self._show_version_messages()

    def _check_update_warning(self):
        """Check for updates and display warning if available"""
        try:
            update_info = self.updater.check_for_updates()

            if update_info.has_update:
                self.display.show_update_available(
                    update_info.current_version, update_info.latest_version
                )
        except:
            pass

    def _show_manifest_messages(self):
        """Show welcome and warning messages from manifest if present"""
        messages = self.manifest_manager.get_messages()

        # Welcome message is now shown in banner - only show warning and note here
        warning = messages.get("warning")
        if warning:
            self.display.show_warning_message(warning)

        note = messages.get("note")
        if note:
            self.display.show_note_message(note)

    def _show_version_messages(self):
        """Show version-specific messages from manifest"""
        try:
            from . import __version__

            version_messages = self.manifest_manager.get_version_messages(__version__)

            for msg in version_messages:
                self.display.show_version_message(msg.message, msg.severity)
        except:
            pass

    def _handle_input(self):
        """Handle user input and execute commands"""
        try:
            current_model = self.models.get_active_model()
            model_name = current_model.name if current_model else "none"
            service_indicator = "🟢" if self.service.is_running() else "🔴"

            # Create colored prompt for readline using ANSI codes (bold blue like rest of app)
            plain_prompt = f"\033[34m\033[1mmoondream-station\033[0m ({model_name}) {service_indicator} > "

            # Use readline for input with proper line editing
            user_input = self._get_input_with_readline(plain_prompt).strip()

            if not user_input:
                return

            if user_input.startswith("/"):
                self._handle_slash_command(user_input)
            else:
                self._execute_command(user_input)

        except EOFError:
            # Ctrl-D just prints a newline and returns empty input, don't exit
            rprint()
            return

    def _get_input_with_readline(self, prompt: str) -> str:
        """Get user input using readline with prompt protection"""
        try:
            # Ensure readline is available and configured
            if readline and hasattr(readline, "get_line_buffer"):
                # Standard input() with readline should protect the prompt
                # Make sure readline editing mode is enabled
                readline.parse_and_bind("set editing-mode emacs")
                return input(prompt)
            else:
                return input(prompt)

        except (ImportError, NameError):
            # Fallback if readline is not available
            return input(prompt)

    def _handle_slash_command(self, command: str):
        """Handle slash commands like /help, /exit"""
        cmd = command[1:].lower()
        if cmd in ["help", "h", "ls"]:
            self.commands.help([])
        elif cmd in ["exit", "quit", "q"]:
            self._exit([])
        elif cmd in ["clear", "cls"]:
            self.commands.clear([])
        elif cmd == "settings":
            self.commands.settings([])
        else:
            self.display.error(f"Unknown slash command: {command}")
            rprint("[dim]Try /help for available commands[/dim]")

    def _execute_command(self, user_input: str):
        """Parse and execute user command"""
        try:
            args = shlex.split(user_input)
            if not args:
                return

            command = args[0].lower()
            command_args = args[1:]

            if command in self.command_map:
                self.command_map[command](command_args)
            else:
                self.display.error(f"Unknown command: {command}")
                rprint("[dim]Type 'help' for available commands[/dim]")

        except ValueError as e:
            self.display.error(f"Invalid command syntax: {e}")

    def _exit(self, args):
        """Exit the REPL"""
        if self.service.is_running():
            with self.display.spinner(self.display.get_random_stopping_message()):
                self.service.stop()

                import time

                time.sleep(0.5)

                if self.service.is_running():
                    rprint(
                        "[yellow]Warning: Service may not have stopped completely[/yellow]"
                    )

        rprint(self.display.get_random_goodbye_message())
        self.running = False
        sys.exit(0)
