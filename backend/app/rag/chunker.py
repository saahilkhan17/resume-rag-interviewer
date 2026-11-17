from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    heading: str
    roles: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


def _split_long_text(text: str, chunk_size: int = 600, overlap: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        target_end = min(start + chunk_size, text_len)
        if target_end == text_len:
            piece = text[start:target_end].strip()
            if piece:
                chunks.append(piece)
            break

        split_point = target_end
        if not text[target_end].isspace():
            search_start = max(start + (chunk_size // 2), start + 1)
            found = -1

            # Priority 1: double newline (paragraph boundary)
            p_break = text.rfind("\n\n", search_start, target_end)
            if p_break != -1:
                found = p_break + 2
            else:
                # Priority 2: single newline
                n_break = text.rfind("\n", search_start, target_end)
                if n_break != -1:
                    found = n_break + 1
                else:
                    # Priority 3: space
                    s_break = text.rfind(" ", search_start, target_end)
                    if s_break != -1:
                        found = s_break + 1

            if found != -1:
                split_point = found
            else:
                # Try forward up to 50 characters to avoid mid-word split
                fwd_space = text.find(" ", target_end, min(target_end + 50, text_len))
                if fwd_space != -1:
                    split_point = fwd_space + 1
                else:
                    split_point = target_end

        piece = text[start:split_point].strip()
        if piece:
            chunks.append(piece)

        # Advance start point taking overlap into account
        next_start = split_point - overlap
        if next_start <= start:
            next_start = split_point
        else:
            # Adjust next_start forward to next whitespace to avoid starting mid-word
            fwd_next = text.find(" ", next_start, min(next_start + 40, split_point))
            if fwd_next != -1:
                next_start = fwd_next + 1

        if next_start <= start:
            next_start = start + 1

        start = next_start

    return chunks


def chunk_markdown(
    text: str,
    source: str,
    roles: list[str],
    topics: list[str],
    chunk_size: int = 600,
    overlap: int = 120,
) -> list[Chunk]:
    if not text or not text.strip():
        return []

    source_stem = Path(source).stem if source else "chunk"
    heading_pattern = re.compile(r"(?m)^(#{1,6}\s+.*)$")
    matches = list(heading_pattern.finditer(text))

    sections: list[tuple[str, str]] = []  # (heading_text, section_body)

    if not matches:
        sections.append(("", text.strip()))
    else:
        # Check text before the first heading
        first_start = matches[0].start()
        if first_start > 0:
            pre_text = text[:first_start].strip()
            if pre_text:
                sections.append(("", pre_text))

        for idx, match in enumerate(matches):
            heading_line = match.group(1)
            clean_heading = heading_line.lstrip("#").strip()
            sec_start = match.start()
            sec_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            sec_body = text[sec_start:sec_end].strip()
            if sec_body:
                sections.append((clean_heading, sec_body))

    chunk_objects: list[Chunk] = []
    chunk_index = 0

    for heading, sec_text in sections:
        pieces = _split_long_text(sec_text, chunk_size=chunk_size, overlap=overlap)
        for piece in pieces:
            chunk_objects.append(
                Chunk(
                    id=f"{source_stem}::{chunk_index}",
                    text=piece,
                    source=source,
                    heading=heading,
                    roles=list(roles),
                    topics=list(topics),
                )
            )
            chunk_index += 1

    return chunk_objects


def chunk_text(
    text: str,
    source: str,
    roles: list[str],
    topics: list[str],
    chunk_size: int = 600,
    overlap: int = 120,
) -> list[Chunk]:
    if not text or not text.strip():
        return []

    source_stem = Path(source).stem if source else "chunk"
    pieces = _split_long_text(text, chunk_size=chunk_size, overlap=overlap)
    return [
        Chunk(
            id=f"{source_stem}::{i}",
            text=piece,
            source=source,
            heading="",
            roles=list(roles),
            topics=list(topics),
        )
        for i, piece in enumerate(pieces)
    ]
