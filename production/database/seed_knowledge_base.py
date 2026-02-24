"""
production/database/seed_knowledge_base.py
CLI script — seed the knowledge_base table from context/product-docs.md.

Usage:
  python -m production.database.seed_knowledge_base

Idempotent: skips entries whose title already exists in the DB.
Requires: OPENAI_API_KEY and POSTGRES_* env vars.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import asyncpg

from production.database.queries import get_db_pool, insert_knowledge_entry

PRODUCT_DOCS_PATH = Path(__file__).parent.parent.parent / "context" / "product-docs.md"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # free local model — no API key needed
EMBEDDING_DIM = 384


def _split_into_sections(content: str) -> list[tuple[str, str]]:
    """
    Split markdown into (title, content) tuples by H2 headings.
    Each section becomes one knowledge base entry.
    """
    sections: list[tuple[str, str]] = []
    current_title = "Introduction"
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append((current_title, body))
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_title, body))

    return sections


async def _get_existing_titles(pool: asyncpg.Pool) -> set[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT title FROM knowledge_base")
    return {r["title"] for r in rows}


def _load_model():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def _embed_local(model, text: str) -> list[float]:
    """Generate embedding locally via fastembed — no API key, no GPU needed."""
    return list(list(model.embed([text[:2000]]))[0])


def _infer_category(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("billing", "payment", "invoice", "subscription")):
        return "billing"
    if any(k in t for k in ("api", "integration", "webhook")):
        return "api"
    if any(k in t for k in ("troubleshoot", "error", "fix", "issue")):
        return "troubleshooting"
    if any(k in t for k in ("account", "profile", "password", "security")):
        return "account"
    if any(k in t for k in ("team", "user", "permission", "admin")):
        return "team_management"
    return "general"


async def main() -> None:
    if not PRODUCT_DOCS_PATH.exists():
        print(f"ERROR: Product docs not found at {PRODUCT_DOCS_PATH}", file=sys.stderr)
        sys.exit(1)

    content = PRODUCT_DOCS_PATH.read_text(encoding="utf-8")
    sections = _split_into_sections(content)
    print(f"Found {len(sections)} sections in product-docs.md")

    print(f"Loading local embedding model '{EMBEDDING_MODEL}' ...")
    model = _load_model()
    print("Model ready.\n")

    pool = await get_db_pool()
    existing = await _get_existing_titles(pool)

    inserted = 0
    skipped = 0

    for title, body in sections:
        if title in existing:
            print(f"  SKIP  {title!r} (already in DB)")
            skipped += 1
            continue

        print(f"  EMBED {title!r} ({len(body)} chars) ...", end=" ", flush=True)
        embedding = _embed_local(model, f"{title}\n\n{body}")
        category = _infer_category(title)
        await insert_knowledge_entry(
            title=title,
            content=body,
            category=category,
            embedding=embedding,
        )
        inserted += 1
        print("OK")

    print(f"\nDone — inserted: {inserted}, skipped: {skipped}")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
