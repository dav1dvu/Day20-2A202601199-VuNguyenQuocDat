"""Search client abstraction for ResearcherAgent."""

import json
import logging
from pathlib import Path
from typing import Any

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client supporting offline corpus and Tavily."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.settings = get_settings()
        self.data_dir = Path(data_dir) if data_dir else Path("data/topics")
        self._corpus_cache: list[dict[str, Any]] | None = None

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Defaults to local JSON corpus in data/topics if available.
        """
        # If Tavily key is provided and valid, try Tavily first
        if self.settings.tavily_api_key:
            try:
                return self._search_tavily(query, max_results)
            except Exception as e:
                logger.warning(f"Tavily search failed ({e}), falling back to local corpus.")

        return self._search_offline_corpus(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        """Search using Tavily API."""
        import requests

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "include_raw_content": False,
        }
        res = requests.post(url, json=payload, timeout=self.settings.timeout_seconds)
        res.raise_for_status()
        data = res.json()

        documents = []
        for item in data.get("results", []):
            documents.append(
                SourceDocument(
                    title=item.get("title", "Untitled"),
                    url=item.get("url"),
                    snippet=item.get("content", ""),
                    metadata={"score": item.get("score")},
                )
            )
        return documents

    def _load_corpus(self) -> list[dict[str, Any]]:
        """Load and cache all articles and source documents from data/topics."""
        if self._corpus_cache is not None:
            return self._corpus_cache

        items: list[dict[str, Any]] = []
        if not self.data_dir.exists():
            # Try alternate path relative to repo root
            alt_path = Path(__file__).resolve().parents[3] / "data" / "topics"
            if alt_path.exists():
                self.data_dir = alt_path

        if self.data_dir.exists():
            for filepath in self.data_dir.glob("*.json"):
                try:
                    with open(filepath, encoding="utf-8") as f:
                        data = json.load(f)

                    # Knowledge base articles
                    kb = data.get("knowledge_base", {})
                    for article in kb.get("knowledge_articles", []):
                        art_id = article.get("article_id", "Article")
                        items.append(
                            {
                                "title": f"[{art_id}] {article.get('title', '')}",
                                "url": f"local://knowledge_articles/{art_id}",
                                "snippet": article.get("content", "")[:1200],
                                "full_text": article.get("content", ""),
                                "source_id": art_id,
                                "topic": data.get("topic", {}).get("name", ""),
                            }
                        )

                    # Source documents
                    for doc in kb.get("source_documents", []):
                        takeaways = "\n".join(doc.get("key_takeaways", []))
                        full_text = doc.get("full_text", "")
                        raw_snip = f"{doc.get('title', '')}\nTakeaways: {takeaways}\n{full_text}"
                        doc_label = doc.get("citation_label") or doc.get("document_id", "Doc")
                        doc_id = doc.get("document_id", "")
                        items.append(
                            {
                                "title": f"[{doc_label}] {doc.get('title', '')}",
                                "url": doc.get("provenance_url")
                                or f"local://source_documents/{doc_id}",
                                "snippet": raw_snip[:1200],
                                "full_text": full_text,
                                "source_id": doc_label,
                                "topic": data.get("topic", {}).get("name", ""),
                            }
                        )
                except Exception as exc:
                    logger.warning(f"Failed to load {filepath}: {exc}")

        self._corpus_cache = items
        return items

    def _search_offline_corpus(self, query: str, max_results: int) -> list[SourceDocument]:
        """Rank and return documents from local offline corpus."""
        corpus = self._load_corpus()
        if not corpus:
            # Fallback placeholder if no files found
            mock_snip = (
                f"Local research summary regarding: {query}. "
                "Multi-agent coordination enables separation of concerns."
            )
            return [
                SourceDocument(
                    title="[local_notes] Multi-Agent Architecture Overview",
                    url="local://notes",
                    snippet=mock_snip,
                    metadata={"source": "local_mock"},
                )
            ]

        query_tokens = [w.lower() for w in query.replace("-", " ").split() if len(w) > 2]
        scored_items: list[tuple[float, dict[str, Any]]] = []

        for item in corpus:
            text = f"{item['title']} {item['topic']} {item['full_text']}".lower()
            score = 0.0
            for token in query_tokens:
                if token in item["title"].lower():
                    score += 5.0
                if token in item["topic"].lower():
                    score += 3.0
                if token in text:
                    score += 1.0 + text.count(token) * 0.1

            if score > 0:
                scored_items.append((score, item))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)

        selected = scored_items[:max_results]
        if not selected and corpus:
            selected = [(1.0, item) for item in corpus[:max_results]]

        results = []
        for score, item in selected:
            results.append(
                SourceDocument(
                    title=item["title"],
                    url=item["url"],
                    snippet=item["snippet"],
                    metadata={"score": score, "source_id": item.get("source_id", "")},
                )
            )

        return results
