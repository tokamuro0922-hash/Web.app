"""
ranking.py — Tech0 Search v1.1
TF-IDF ベースの検索エンジン（SearchEngine クラス）を提供する。
本文検索を強めた改善版。
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List
from datetime import datetime


class SearchEngine:
    """TF-IDFベースの検索エンジン"""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=8000,
            analyzer="char_wb",
            ngram_range=(2, 4),
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
            self.pages = []
            self.tfidf_matrix = None
            self.is_fitted = False
            return

        self.pages = pages
        corpus = []

        for p in pages:
            kw = p.get("keywords", "") or ""
            if isinstance(kw, str):
                kw_list = [k.strip() for k in kw.split(",") if k.strip()]
            else:
                kw_list = [str(k).strip() for k in kw if str(k).strip()]

            title = str(p.get("title", "") or "")
            description = str(p.get("description", "") or "")
            full_text = str(p.get("full_text", "") or "")
            keywords_text = " ".join(kw_list)

            # 本文を強めに評価する
            text = " ".join([
                (title + " ") * 2,
                (description + " ") * 2,
                (full_text + " ") * 4,
                (keywords_text + " ") * 2,
            ])
            corpus.append(text)

        doc_count = len(corpus)
        max_df = 1.0 if doc_count < 2 else 0.95

        self.vectorizer = TfidfVectorizer(
            max_features=8000,
            analyzer="char_wb",
            ngram_range=(2, 4),
            min_df=1,
            max_df=max_df,
            sublinear_tf=True
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self.is_fitted = True

    def search(self, query: str, top_n: int = 20) -> list:
        """TF-IDF ベースの検索を実行する"""
        if not self.is_fitted or not query.strip():
            return []

        query = self._normalize_query(query)
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        results = []
        for idx, base_score in enumerate(similarities):
            if base_score > 0:
                page = self.pages[idx].copy()
                final_score = self._calculate_final_score(page, float(base_score), query)
                page["relevance_score"] = round(final_score * 100, 1)
                page["base_score"] = round(float(base_score) * 100, 1)
                results.append(page)

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_n]

    def _normalize_query(self, query: str) -> str:
        """検索クエリを正規化する"""
        return query.replace("　", " ").strip().lower()

    def _calculate_final_score(self, page: dict, base_score: float, query: str) -> float:
        """複数要素を組み合わせて最終スコアを計算する"""
        score = base_score
        query_lower = query.lower()

        title = str(page.get("title", "") or "").lower()
        description = str(page.get("description", "") or "").lower()
        full_text = str(page.get("full_text", "") or "").lower()

        # タイトル一致
        if query_lower == title:
            score *= 1.6
        elif query_lower in title:
            score *= 1.3

        # 説明文一致
        if query_lower and query_lower in description:
            score *= 1.15

        # 本文一致を強める
        if query_lower and query_lower in full_text:
            score *= 1.5

        keywords = page.get("keywords", [])
        if isinstance(keywords, str):
            keywords = keywords.split(",")
        keywords_lower = [str(k).strip().lower() for k in keywords if str(k).strip()]
        if query_lower in keywords_lower:
            score *= 1.25

        # 新しさボーナス
        crawled_at = page.get("crawled_at", "")
        if crawled_at:
            try:
                crawled = datetime.fromisoformat(str(crawled_at).replace("Z", "+00:00"))
                days_old = (datetime.now() - crawled.replace(tzinfo=None)).days
                if days_old <= 90:
                    recency_bonus = 1 + (0.15 * (90 - days_old) / 90)
                    score *= recency_bonus
            except Exception:
                pass

        # 文章量による調整
        word_count = page.get("word_count", 0)
        try:
            word_count = int(word_count)
        except Exception:
            word_count = 0

        if word_count < 20:
            score *= 0.75
        elif word_count < 50:
            score *= 0.9
        elif word_count > 20000:
            score *= 0.9

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