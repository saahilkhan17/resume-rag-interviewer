from pathlib import Path
from typing import Any
from app.rag.chunker import Chunk, chunk_markdown, chunk_text
from app.rag.vector_store import VectorStore


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text:
        return {}, ""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, text

    fm_text = "\n".join(lines[1:end_idx]).strip()
    body = "\n".join(lines[end_idx + 1:]).strip()

    metadata: dict[str, Any] = {}
    try:
        import yaml

        loaded = yaml.safe_load(fm_text)
        if isinstance(loaded, dict):
            for k, v in loaded.items():
                if isinstance(v, list):
                    metadata[k] = [str(item).strip() for item in v]
                else:
                    metadata[k] = v
            return metadata, body
    except Exception:
        pass

    current_key = None
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line and not line.startswith("-"):
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
                metadata[key] = items
                current_key = None
            elif not val:
                metadata[key] = []
                current_key = key
            else:
                metadata[key] = val.strip("'\"")
                current_key = None
        elif line.startswith("-") and current_key is not None:
            val = line.lstrip("-").strip().strip("'\"")
            if val:
                if not isinstance(metadata.get(current_key), list):
                    metadata[current_key] = []
                metadata[current_key].append(val)

    return metadata, body


def load_kb(kb_dir: Path) -> list[Chunk]:
    kb_path = Path(kb_dir)
    if not kb_path.exists() or not kb_path.is_dir():
        print(f"Warning: KB directory {kb_path} does not exist.")
        return []

    supported_exts = {".md", ".txt", ".pdf"}
    files = sorted(
        [
            p
            for p in kb_path.iterdir()
            if p.is_file() and p.suffix.lower() in supported_exts
        ]
    )

    chunks: list[Chunk] = []
    for file_path in files:
        ext = file_path.suffix.lower()
        if ext == ".md":
            try:
                content = file_path.read_text(encoding="utf-8")
                metadata, body = parse_frontmatter(content)
                roles = metadata.get("roles", [])
                topics = metadata.get("topics", [])
                file_chunks = chunk_markdown(
                    text=body,
                    source=file_path.name,
                    roles=roles,
                    topics=topics,
                )
                chunks.extend(file_chunks)
            except Exception as e:
                print(f"Warning: Failed to load markdown file {file_path.name}: {e}")
        elif ext == ".txt":
            try:
                content = file_path.read_text(encoding="utf-8")
                metadata, body = parse_frontmatter(content)
                roles = metadata.get("roles", [])
                topics = metadata.get("topics", [])
                file_chunks = chunk_text(
                    text=body,
                    source=file_path.name,
                    roles=roles,
                    topics=topics,
                )
                chunks.extend(file_chunks)
            except Exception as e:
                print(f"Warning: Failed to load text file {file_path.name}: {e}")
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(file_path))
                extracted_pages = []
                for page in reader.pages:
                    pt = page.extract_text()
                    if pt:
                        extracted_pages.append(pt)
                pdf_text = "\n\n".join(extracted_pages)
                if not pdf_text.strip():
                    print(
                        f"Warning: PDF file {file_path.name} contained no extractable text, skipping."
                    )
                    continue
                metadata, body = parse_frontmatter(pdf_text)
                roles = metadata.get("roles", [])
                topics = metadata.get("topics", [])
                file_chunks = chunk_text(
                    text=body,
                    source=file_path.name,
                    roles=roles,
                    topics=topics,
                )
                chunks.extend(file_chunks)
            except Exception as e:
                print(f"Warning: Failed to load PDF file {file_path.name}: {e}")

    return chunks


def build_index(kb_dir: Path, index_dir: Path) -> VectorStore:
    chunks = load_kb(kb_dir)
    store = VectorStore(index_dir=index_dir)
    store.build(chunks)
    return store


def main() -> None:
    import argparse
    from app.config import settings

    parser = argparse.ArgumentParser(description="Ingest KB documents and build index")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild vector store index from KB directory",
    )
    parser.add_argument(
        "--kb-dir",
        type=str,
        default=None,
        help="Path to KB directory (defaults to settings.kb_dir_path)",
    )
    parser.add_argument(
        "--index-dir",
        type=str,
        default=None,
        help="Path to index output directory (defaults to backend/data/vector_store)",
    )
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir) if args.kb_dir else settings.kb_dir_path
    if not kb_dir.is_absolute():
        kb_dir = settings.backend_dir / kb_dir

    if args.index_dir:
        index_dir = Path(args.index_dir)
        if not index_dir.is_absolute():
            index_dir = settings.backend_dir / index_dir
    else:
        index_dir = settings.backend_dir / "data" / "vector_store"

    print(f"Ingesting KB from: {kb_dir} -> {index_dir}")
    store = build_index(kb_dir=kb_dir, index_dir=index_dir)
    print(f"Finished building index with {store.chunk_count} chunks at {index_dir}")


if __name__ == "__main__":
    main()
