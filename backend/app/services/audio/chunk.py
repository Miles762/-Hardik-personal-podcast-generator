"""Script chunking for TTS (PRD 9).

Split the script into paragraph-sized chunks small enough for clean TTS but
large enough to preserve prosody. Pure and deterministic → unit-tested. The
chunk list feeds request-stitching: each chunk knows its previous/next text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Soft cap per chunk. ElevenLabs handles long text, but shorter chunks fail
# faster and stitch better; ~800 chars ≈ a healthy paragraph.
MAX_CHUNK_CHARS = 800


@dataclass(frozen=True)
class Chunk:
    text: str
    previous_text: str  # tail of the prior chunk (prosody continuity)
    next_text: str      # head of the next chunk


def _split_paragraphs(script: str) -> list[str]:
    # Split on blank lines first; fall back to sentence grouping for long blocks.
    paras = [p.strip() for p in re.split(r"\n\s*\n", script.strip()) if p.strip()]
    out: list[str] = []
    for para in paras:
        if len(para) <= MAX_CHUNK_CHARS:
            out.append(para)
            continue
        # Long paragraph: split into sentences, greedily packed under the cap.
        sentences = re.split(r"(?<=[.!?])\s+", para)
        buf = ""
        for sentence in sentences:
            if buf and len(buf) + len(sentence) + 1 > MAX_CHUNK_CHARS:
                out.append(buf.strip())
                buf = sentence
            else:
                buf = f"{buf} {sentence}".strip()
        if buf:
            out.append(buf.strip())
    return out


def chunk_script(script: str, *, context_chars: int = 200) -> list[Chunk]:
    """Split into stitched chunks. ``context_chars`` bounds the stitching hints."""
    paras = _split_paragraphs(script)
    chunks: list[Chunk] = []
    for i, text in enumerate(paras):
        prev = paras[i - 1][-context_chars:] if i > 0 else ""
        nxt = paras[i + 1][:context_chars] if i < len(paras) - 1 else ""
        chunks.append(Chunk(text=text, previous_text=prev, next_text=nxt))
    return chunks
