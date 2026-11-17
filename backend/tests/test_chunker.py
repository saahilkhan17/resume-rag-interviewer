import pytest
from app.rag.chunker import chunk_markdown, chunk_text, Chunk

@pytest.fixture
def long_text():
    # Generate a long repetitive text with headings
    heading = "# Heading One"
    body = " ".join(["word"] * 300)  # ~1500 chars when repeated
    return f"{heading}\n\n{body}\n\n## Subheading\n\n{body}"  # two sections

def test_chunk_markdown_splits_on_headings():
    text = "# H1\nContent A\n\n## H2\nContent B"
    chunks = chunk_markdown(text, source="file.md", roles=[], topics=[])
    ids = [c.id for c in chunks]
    # Expect three chunks: pre-heading (empty ignored), H1 section, H2 section
    assert len(chunks) == 2
    assert chunks[0].heading == "H1"
    assert chunks[1].heading == "H2"
    # IDs include source stem and index
    assert ids[0].startswith("file::0")
    assert ids[1].startswith("file::1")

def test_chunk_text_simple():
    txt = "plain text without headings"
    chunks = chunk_text(txt, source="plain.txt", roles=[], topics=[])
    assert len(chunks) == 1
    assert chunks[0].heading == ""
    assert chunks[0].text == txt.strip()

def test_split_long_text_overlap():
    # Use chunk_markdown with a long body to test overlap
    body = " ".join(["word"] * 1000)  # long body
    text = f"# Title\n{body}"
    chunks = chunk_markdown(text, source="doc.md", roles=[], topics=[], chunk_size=600, overlap=120)
    # Ensure overlap: next chunk starts within previous tail
    assert len(chunks) >= 2
    first, second = chunks[0].text, chunks[1].text
    # The start of second should be found in the tail of first
    assert second[:20] in first[-120:]

def test_empty_input_returns_empty():
    assert chunk_markdown("   \n  ", source="empty.md", roles=[], topics=[]) == []
    assert chunk_text("   \n", source="empty.txt", roles=[], topics=[]) == []

def test_chunk_ids_unique_and_formatted():
    txt = "# H\nA"
    chunks = chunk_markdown(txt, source="file.md", roles=[], topics=[])
    ids = [c.id for c in chunks]
    assert len(set(ids)) == len(ids)
    assert all("::" in cid for cid in ids)
