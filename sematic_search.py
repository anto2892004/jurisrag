import sys
import os
from pinecone import Pinecone
from config import PINECONE_CONFIG
from generate_embedding import get_reduced_embedding

# Init Pinecone client
pc = Pinecone(api_key=PINECONE_CONFIG["api_key"])
index = pc.Index(PINECONE_CONFIG["index_name"])

def semantic_search(query: str, top_k: int = 5):
    """Search Pinecone for top_k most relevant chunks"""
    query_embedding = get_reduced_embedding(query)

    results = index.query(
        vector=query_embedding.tolist(),
        top_k=top_k,
        include_metadata=True
    )

    matches = []
    for match in results["matches"]:
        matches.append({
            "score": match["score"],
            "case_id": match["metadata"].get("case_id"),
            "chunk_id": match["metadata"].get("chunk_id"),
            "court": match["metadata"].get("court"),
            "jurisdiction": match["metadata"].get("jurisdiction"),
            "outcome": match["metadata"].get("outcome"),
            "statutes": match["metadata"].get("statutes"),
            "text": match["metadata"].get("text")
        })

    return matches


if __name__ == "__main__":
    query = "personal liberty under Article 21 of the Constitution"
    results = semantic_search(query, top_k=3)

    print("\n🔍 Search Results:")
    for r in results:
        print(f"[{r['score']:.4f}] Case: {r['case_id']} Chunk: {r['chunk_id']}")
        print(f"Text: {r['text'][:250]}...\n")
