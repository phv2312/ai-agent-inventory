"""Decode incremental chars from a streamed JSON widget_code value."""

import re


class WidgetCodeStreamExtractor:
    """Decode incremental chars from a streamed JSON widget_code value."""

    def __init__(self) -> None:
        self._buffer = ""
        self._mode: str = "seek"
        self._cursor = 0

    def feed(self, chunk: str) -> str:
        """Feed a JSON args delta; return newly decoded widget_code chars."""
        self._buffer += chunk
        out: list[str] = []
        if self._mode == "seek":
            m = re.search(r'"widget_code"\s*:\s*"', self._buffer)
            if not m:
                return ""
            self._mode = "string"
            self._cursor = m.end()

        if self._mode != "string":
            return ""

        while self._cursor < len(self._buffer):
            c = self._buffer[self._cursor]
            if c == "\\":
                if self._cursor + 1 >= len(self._buffer):
                    break
                esc = self._buffer[self._cursor + 1]
                if esc == "n":
                    out.append("\n")
                elif esc == "t":
                    out.append("\t")
                elif esc == "r":
                    out.append("\r")
                elif esc in '"\\/':
                    out.append(esc)
                elif esc == "u":
                    if self._cursor + 6 > len(self._buffer):
                        break
                    hexpart = self._buffer[self._cursor + 2 : self._cursor + 6]
                    try:
                        out.append(chr(int(hexpart, 16)))
                    except ValueError:
                        out.append(esc)
                    self._cursor += 6
                    continue
                else:
                    out.append(esc)
                self._cursor += 2
                continue
            if c == '"':
                self._mode = "done"
                self._cursor += 1
                break
            out.append(c)
            self._cursor += 1

        return "".join(out)
