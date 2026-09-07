import re
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.database import get_connection

class VectorStore:
    def __init__(self):
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._chunk_metadata: List[Dict[str, Any]] = []
        self._is_indexed = False

    def build_index(self):
        """Builds or rebuilds the in-memory retrieval index from SQLite chunks."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.material_id, c.chunk_index, c.page_number, c.heading, c.content, c.token_count,
                   m.filename, m.display_name, m.subject
            FROM document_chunks c
            JOIN course_materials m ON c.material_id = m.id
            ORDER BY c.material_id, c.chunk_index
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self._vectorizer = None
            self._tfidf_matrix = None
            self._chunk_metadata = []
            self._is_indexed = False
            return

        corpus = []
        metadata = []
        for r in rows:
            text = f"{r['heading'] or ''} {r['content']}".strip()
            corpus.append(text)
            metadata.append({
                "chunk_id": r["id"],
                "material_id": r["material_id"],
                "chunk_index": r["chunk_index"],
                "page_number": r["page_number"],
                "heading": r["heading"],
                "content": r["content"],
                "token_count": r["token_count"],
                "filename": r["filename"],
                "display_name": r["display_name"],
                "subject": r["subject"]
            })

        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            sublinear_tf=True,
            max_df=0.95
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(corpus)
        self._chunk_metadata = metadata
        self._is_indexed = True

    def search(
        self, 
        query: str, 
        top_k: int = 4, 
        material_id: Optional[int] = None,
        min_score: float = 0.02
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search across course material chunks with keyword boosting.
        """
        if not self._is_indexed or self._vectorizer is None or self._tfidf_matrix is None:
            self.build_index()
            if not self._is_indexed:
                return []

        if not query.strip():
            return []

        # Vectorize query
        try:
            query_vec = self._vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self._tfidf_matrix)[0]
        except Exception:
            return []

        # Extract keywords for exact boost
        raw_terms = [re.escape(w.lower()) for w in re.findall(r'\b[a-zA-Z0-9_\-]{3,}\b', query)]

        results = []
        for idx, base_score in enumerate(similarities):
            meta = self._chunk_metadata[idx]

            # Filter by material if requested
            if material_id is not None and meta["material_id"] != material_id:
                continue

            content_lower = meta["content"].lower()
            heading_lower = (meta["heading"] or "").lower()

            # Boost if query keywords appear in heading or text
            keyword_matches = sum(1 for term in raw_terms if re.search(r'\b' + term + r'\b', content_lower))
            heading_matches = sum(1 for term in raw_terms if re.search(r'\b' + term + r'\b', heading_lower))

            boost = (keyword_matches * 0.08) + (heading_matches * 0.15)
            final_score = float(base_score + boost)

            if final_score >= min_score or base_score > 0.05:
                item = dict(meta)
                item["similarity_score"] = round(min(1.0, final_score), 4)
                item["raw_cosine"] = round(float(base_score), 4)
                results.append(item)

        # Sort descending by final score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

# Global singleton indexer
vector_store = VectorStore()
