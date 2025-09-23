try:
    import readline
except ImportError:
    readline = None
from typing import List, Optional


class TabCompleter:
    def __init__(self, repl_session):
        self.repl = repl_session
        self.commands = list(repl_session.command_map.keys())
        self.setup_completion()
    
    def setup_completion(self):
        """Setup tab completion"""
        if readline:
            try:
                readline.set_completer(self.complete)
                readline.parse_and_bind("tab: complete")
                readline.set_completer_delims(" \t\n")
            except Exception:
                pass
    
    def complete(self, text: str, state: int) -> Optional[str]:
        """Tab completion function"""
        if not readline:
            return None
        line = readline.get_line_buffer()
        tokens = line.split()
        
        if not tokens or (len(tokens) == 1 and not line.endswith(' ')):
            matches = self._complete_command(text)
        else:
            command = tokens[0]
            if command == 'models':
                matches = self._complete_models_subcommand(tokens, text)
            elif command == 'settings':
                matches = self._complete_settings_subcommand(tokens, text)
            elif command in ['start', 'switch']:
                matches = self._complete_model_names(text)
            else:
                matches = []
        
        try:
            return matches[state]
        except IndexError:
            return None
    
    def _complete_command(self, text: str) -> List[str]:
        """Complete main commands"""
        return [cmd for cmd in self.commands if cmd.startswith(text)]
    
    def _complete_models_subcommand(self, tokens: List[str], text: str) -> List[str]:
        """Complete models subcommands"""
        if len(tokens) == 2:
            subcommands = ['list', 'switch', 'add']
            return [sub for sub in subcommands if sub.startswith(text)]
        elif len(tokens) == 3 and tokens[1] == 'switch':
            return self._complete_model_names(text)
        return []
    
    def _complete_settings_subcommand(self, tokens: List[str], text: str) -> List[str]:
        """Complete settings subcommands"""
        if len(tokens) == 2:
            subcommands = ['set', 'manifest']
            return [sub for sub in subcommands if sub.startswith(text)]
        elif len(tokens) == 3 and tokens[1] == 'set':
            settable_keys = [
                'inference_workers', 'inference_max_queue_size',
                'inference_timeout', 'auto_start'
            ]
            return [key for key in settable_keys if key.startswith(text)]
        elif len(tokens) == 3 and tokens[1] == 'manifest':
            manifest_subcommands = ['load']
            return [sub for sub in manifest_subcommands if sub.startswith(text)]
        return []
    
    def _complete_model_names(self, text: str) -> List[str]:
        """Complete model names"""
        model_names = self.repl.models.list_models()
        return [name for name in model_names if name.startswith(text)]