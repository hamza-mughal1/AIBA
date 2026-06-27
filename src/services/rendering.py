import shutil

from rich.console import Console
from rich.markdown import Markdown

C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "purple": "\033[38;5;99m",
    "teal": "\033[38;5;44m",
    "green": "\033[38;5;42m",
    "yellow": "\033[38;5;221m",
    "red": "\033[38;5;203m",
}


def _width() -> int:
    return shutil.get_terminal_size().columns


_console = Console(highlight=False)


def render_markdown(text: str) -> None:
    md = Markdown(text, code_theme="monokai")
    _console.print(md)


def hr(char: str = "─", color: str = "dim") -> str:
    return f"{C[color]}{char * _width()}{C['reset']}"


def badge(label: str, value: str) -> str:
    return f"  {C['dim']}{label}:{C['reset']}  {C['teal']}{value}{C['reset']}"
