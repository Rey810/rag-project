"""Work out which retrieved sources the answer actually drew on.

The system prompt numbers every context entry and asks the model to finish with a
single line such as ``[USED_SOURCES: 1, 3]`` (or ``[USED_SOURCES: none]``). These
helpers strip that line from the streamed answer and turn it into a filter for the
source chips shown under the reply, so unrelated retrievals are not presented as
if they backed the answer.
"""

import re

USED_SOURCES_MARKER = "[USED_SOURCES:"
_USED_SOURCES_RE = re.compile(r"\s*\[USED_SOURCES:\s*([^\]]*)\]\s*")


def holdback_index(pending: str) -> int:
    """Return how much of ``pending`` is safe to emit to the client.

    Everything after the returned index is either trailing whitespace or text that
    could still turn out to be the ``[USED_SOURCES: ...]`` line, so it stays
    buffered until more text arrives or the stream ends.
    """
    safe = len(pending.rstrip())
    start = pending.find("[")
    while start != -1 and start < safe:
        tail = pending[start:]
        if tail.startswith(USED_SOURCES_MARKER) or USED_SOURCES_MARKER.startswith(tail):
            return min(safe, len(pending[:start].rstrip()))
        start = pending.find("[", start + 1)
    return safe


def split_used_sources(text: str) -> tuple[str, set[int] | None]:
    """Remove the marker line from ``text``.

    Returns the cleaned text and the set of Source Numbers the model reported.
    The set is ``None`` when no marker was found, which callers should treat as
    "unknown" rather than "none".
    """
    match = _USED_SOURCES_RE.search(text)
    if not match:
        return text, None
    numbers = {int(n) for n in re.findall(r"\d+", match.group(1))}
    cleaned = (text[: match.start()] + text[match.end():]).rstrip()
    return cleaned, numbers


def select_sources(sources: list[dict], used: set[int] | None) -> list[dict]:
    """Keep only sources backed by at least one used chunk number.

    Each source carries ``chunk_numbers`` (the 1-based numbers shown to the model);
    that field is dropped from the returned copies. If ``used`` is ``None`` the
    model gave no marker, so every source is returned rather than hiding
    potentially relevant ones.
    """
    selected = []
    for source in sources:
        chunk_numbers = source.get("chunk_numbers", [])
        if used is None or any(n in used for n in chunk_numbers):
            selected.append({k: v for k, v in source.items() if k != "chunk_numbers"})
    return selected
