"""
ranking.py — Tech0 Search v1.0
TF-IDF ベースの検索エンジン（SearchEngine クラス）を提供する。
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List
from datetime import datetime


class SearchEngine:
    """TF-IDFベースの検索エンジン"""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True
        )
        self.tfidf_matrix = None
        self.pages = []
        self.is_fitted = False

    def build_index(self, pages: list):
        """全ページの TF-IDF インデックスを構築する"""
        if not pages:
            return

        self.pages = pages
        corpus = []

        for p in pages:
            kw = p.get("keywords", "") or ""
            if isinstance(kw, str):
                kw_list = [k.strip() for k in kw.split(",") if k.strip()]
            else:
                kw_list = kw

            text = " ".join([
                (p.get("title", "") + " ") * 3,
                (p.get("description", "") + " ") * 2,
                (p.get("full_text", "") + " "),
                (" ".join(kw_list) + " ") * 2,
            ])
            corpus.append(text)

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self.is_fitted = True

    def search(self, query: str, top_n: int = 20) -> list:
        """TF-IDF ベースの検索を実行する"""
        if not self.is_fitted or not query.strip():
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        results = []
        for idx, base_score in enumerate(similarities):
            if base_score > 0.01:
                page = self.pages[idx].copy()
                final_score = self._calculate_final_score(page, base_score, query)
                page["relevance_score"] = round(float(final_score) * 100, 1)
                page["base_score"] = round(float(base_score) * 100, 1)
                results.append(page)

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_n]

    def _calculate_final_score(self, page: dict, base_score: float, query: str) -> float:
        """複数要素を組み合わせて最終スコアを計算する"""
        score = base_score
        query_lower = query.lower()

        title = page.get("title", "").lower()
        if query_lower == title:
            score *= 1.8
        elif query_lower in title:
            score *= 1.4

        keywords = page.get("keywords", [])
        if isinstance(keywords, str):
            keywords = keywords.split(",")
        keywords_lower = [k.strip().lower() for k in keywords]
        if query_lower in keywords_lower:
            score *= 1.3

        crawled_at = page.get("crawled_at", "")
        if crawled_at:
            try:
                crawled = datetime.fromisoformat(crawled_at.replace("Z", "+00:00"))
                days_old = (datetime.now() - crawled.replace(tzinfo=None)).days
                if days_old <= 90:
                    recency_bonus = 1 + (0.2 * (90 - days_old) / 90)
                    score *= recency_bonus
            except Exception:
                pass

        word_count = page.get("word_count", 0)
        if word_count < 50:
            score *= 0.7
        elif word_count > 10000:
            score *= 0.85

        return score


_engine = None


def get_engine() -> SearchEngine:
    """検索エンジンのシングルトンを取得する"""
    global _engine
    if _engine is None:
        _engine = SearchEngine()
    return _engine


def rebuild_index(pages: List[dict]):
    """インデックスを再構築する"""
    engine = get_engine()
    engine.build_index(pages)

