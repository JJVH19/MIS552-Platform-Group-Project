"""Court and event discovery: BM25, semantic vectors, and RRF hybrid ranking.

Optional structured filters constrain the candidate pool *before* top-k selection.
MiniLM is used where available. A lexical TF-IDF fallback is explicitly labeled.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def documents(kind: Literal["courts", "events"]) -> list[dict]:
    if kind not in ("courts", "events"):
        raise ValueError("kind must be courts or events")
    filename = "facilities.json" if kind == "courts" else "events.json"
    return json.loads((ROOT / "data" / filename).read_text(encoding="utf8"))


def text_for(item: dict, kind: str) -> str:
    if kind == "courts":
        return " ".join([
            item["name"], item["city"], item["description"],
            "indoor" if item["indoor"] else "outdoor",
            " ".join(item["amenities"]), "basketball court gym venue facility",
        ])
    return " ".join([
        item["name"], item["city"], item["description"],
        item["format"], item["skill_level"], item["date"],
        "basketball tournament event",
    ])


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [tokenize(text) for text in texts]
        self.n = len(self.docs)
        self.dl = [len(doc) for doc in self.docs]
        self.avgdl = sum(self.dl) / max(self.n, 1)
        self.tf = [Counter(doc) for doc in self.docs]
        df = Counter()
        for doc in self.docs:
            df.update(set(doc))
        self.idf = {
            term: math.log(1 + (self.n - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }
        self.k1 = k1
        self.b = b

    def score(self, query: str) -> np.ndarray:
        scores = []
        for tf, dl in zip(self.tf, self.dl):
            value = 0.0
            for term in set(tokenize(query)):
                if term not in tf:
                    continue
                freq = tf[term]
                value += self.idf.get(term, 0) * (
                    freq * (self.k1 + 1)
                ) / (
                    freq + self.k1 * (1 - self.b + self.b * dl / max(self.avgdl, 1))
                )
            scores.append(value)
        return np.array(scores, dtype=float)


@lru_cache(maxsize=1)
def _embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception:
        return None


@lru_cache(maxsize=2)
def _prepared(kind: str):
    items = documents(kind)
    texts = [text_for(item, kind) for item in items]
    return items, texts, BM25(texts)


@lru_cache(maxsize=2)
def _vectors(kind: str):
    model = _embedding_model()
    if model is None:
        return None
    _, texts, _ = _prepared(kind)
    path = ROOT / "indexes" / f"{kind}_embeddings.npy"
    matrix = None
    if path.exists():
        try:
            candidate = np.load(path)
            if candidate.ndim == 2 and candidate.shape[0] == len(texts):
                matrix = candidate
        except Exception:
            pass
    if matrix is None:
        matrix = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return np.asarray(matrix, dtype=float)


def vector_scores(query: str, kind: str):
    model = _embedding_model()
    matrix = _vectors(kind)
    if model is None or matrix is None:
        return None
    query_vector = model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
    return matrix @ query_vector


def _rank(scores: np.ndarray, candidates: list[int] | None = None) -> list[int]:
    indices = list(range(len(scores))) if candidates is None else candidates
    return sorted(indices, key=lambda i: (-float(scores[i]), i))


def _normalize_filters(kind: str, filters: dict | None) -> dict:
    """Validate known filters so typos cannot silently return misleading results."""
    if filters is None:
        return {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be a dictionary")
    valid_keys = {"city", "indoor", "amenities", "max_hourly_rate"} if kind == "courts" else {
        "city", "skill_level", "format"
    }
    unknown = set(filters) - valid_keys
    if unknown:
        raise ValueError("Unsupported filters: " + ", ".join(sorted(unknown)))
    out = {}
    for key in ("city", "skill_level", "format"):
        if key not in filters or filters[key] is None or filters[key] == "":
            continue
        if not isinstance(filters[key], str):
            raise ValueError(f"{key} must be a string")
        out[key] = filters[key].strip().casefold()
    if kind == "courts":
        if "indoor" in filters and filters["indoor"] is not None:
            if not isinstance(filters["indoor"], bool):
                raise ValueError("indoor must be True, False, or None")
            out["indoor"] = filters["indoor"]
        if "amenities" in filters and filters["amenities"]:
            amenities = filters["amenities"]
            if isinstance(amenities, str):
                amenities = [amenities]
            if not isinstance(amenities, (list, tuple, set)) or any(
                not isinstance(a, str) for a in amenities
            ):
                raise ValueError("amenities must be a list of strings")
            out["amenities"] = {a.strip().casefold() for a in amenities if a.strip()}
        if "max_hourly_rate" in filters and filters["max_hourly_rate"] is not None:
            rate = filters["max_hourly_rate"]
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate < 0:
                raise ValueError("max_hourly_rate must be a nonnegative number")
            out["max_hourly_rate"] = float(rate)
    return out


def _matches(item: dict, kind: str, filters: dict) -> bool:
    if "city" in filters and item.get("city", "").casefold() != filters["city"]:
        return False
    if kind == "events":
        if "skill_level" in filters and item.get("skill_level", "").casefold() != filters["skill_level"]:
            return False
        if "format" in filters and item.get("format", "").casefold() != filters["format"]:
            return False
    else:
        if "indoor" in filters and item.get("indoor") is not filters["indoor"]:
            return False
        if "amenities" in filters and not filters["amenities"].issubset(
            {a.casefold() for a in item.get("amenities", [])}
        ):
            return False
        if "max_hourly_rate" in filters and float(item.get("hourly_rate", float("inf"))) > filters["max_hourly_rate"]:
            return False
    return True


def search(
    query: str,
    kind: Literal["courts", "events"] = "courts",
    method: str = "hybrid",
    k: int = 5,
    filters: dict | None = None,
) -> dict:
    """Rank only listings meeting every structured filter.

    Existing positional calls stay compatible: search(query, kind, method, k).
    Supported event filters: city, skill_level, format.
    Supported court filters: city, indoor, amenities (all), max_hourly_rate.
    """
    if kind not in ("courts", "events"):
        raise ValueError("Invalid search category")
    if method not in ("keyword", "semantic", "hybrid"):
        raise ValueError("Invalid search method")
    normalized = _normalize_filters(kind, filters)
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    if not query.strip():
        return {"results": [], "mode": "none", "warning": "Enter a search query.", "total_candidates": 0}
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")

    items, texts, bm25 = _prepared(kind)
    candidates = [i for i, item in enumerate(items) if _matches(item, kind, normalized)]
    if not candidates:
        return {
            "results": [], "mode": "No listings meet selected filters", "warning": None,
            "total_candidates": 0,
        }

    keyword = bm25.score(query)
    warning = None
    if method == "keyword":
        mode = "BM25 keyword ranking"
        order = _rank(keyword, candidates)
        scores = keyword
    else:
        semantic = vector_scores(query, kind)
        if semantic is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            cv = TfidfVectorizer(ngram_range=(1, 2))
            matrix = cv.fit_transform(texts)
            semantic = cosine_similarity(cv.transform([query]), matrix).ravel()
            mode = "lexical TF-IDF fallback (no sentence-transformer model)"
            warning = (
                "Semantic model unavailable. Vector/hybrid ranking uses lexical "
                "TF-IDF, not semantic embeddings."
            )
        else:
            mode = "MiniLM semantic embeddings"

        semantic_rank = _rank(semantic, candidates)
        if method == "semantic":
            order = semantic_rank
            scores = semantic
        else:
            keyword_rank = _rank(keyword, candidates)
            rrf = np.zeros(len(items), dtype=float)
            for ranking in (keyword_rank, semantic_rank):
                for rank, idx in enumerate(ranking, start=1):
                    rrf[idx] += 1 / (60 + rank)
            order = _rank(rrf, candidates)
            scores = rrf

    results = []
    for idx in order[:k]:
        record = dict(items[idx])
        record["score"] = round(float(scores[idx]), 6)
        record["why_match"] = (
            f"Passed all selected filters; ranked using {method} on its "
            "title, city, description and relevant attributes."
        )
        results.append(record)
    return {
        "results": results,
        "mode": mode,
        "warning": warning,
        "total_candidates": len(candidates),
    }


def search_courts(query: str, method="hybrid", k=5, filters: dict | None = None) -> list[dict]:
    return search(query, "courts", method, k, filters=filters)["results"]


def search_events(query: str, method="hybrid", k=5, filters: dict | None = None) -> list[dict]:
    return search(query, "events", method, k, filters=filters)["results"]
