import shutil
import sys


class Console:
    """Thin wrapper over stdin/stdout so prompts are testable."""

    _last_status = ""

    def input(self, prompt: str = "") -> str:
        return input(prompt)

    def print(self, *args: object) -> None:
        print(*args)

    @staticmethod
    def _width() -> int:
        # One column short of the terminal width: writing into the last column makes many
        # terminals wrap, which turns every "in-place" update into a new line.
        return max(shutil.get_terminal_size((80, 24)).columns - 1, 20)

    def status(self, line: str) -> None:
        """Overwrite the current terminal line (live countdowns). Redraws only on change."""
        width = self._width()
        text = line[:width].ljust(width)
        if text == self._last_status:
            return
        self._last_status = text
        sys.stdout.write("\r" + text)
        sys.stdout.flush()

    def clear_status(self) -> None:
        if self._last_status:
            sys.stdout.write("\r" + " " * self._width() + "\r")
            sys.stdout.flush()
            self._last_status = ""


class FakeConsole:
    def __init__(self, inputs: list[str] | None = None):
        self.inputs = list(inputs or [])
        self.output: list[str] = []

    def input(self, prompt: str = "") -> str:
        self.output.append(prompt)
        if not self.inputs:
            raise EOFError("FakeConsole ran out of scripted input")
        return self.inputs.pop(0)

    def print(self, *args: object) -> None:
        self.output.append(" ".join(str(a) for a in args))

    def status(self, line: str) -> None:
        self.output.append(line)

    def clear_status(self) -> None:
        pass

    @property
    def text(self) -> str:
        return "\n".join(self.output)
