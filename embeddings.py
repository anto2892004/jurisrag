# embeddings.py
import numpy as np
import pickle
from openai import OpenAI
from elasticsearch import Elasticsearch
from pinecone import Pinecone

# ---------------- CONFIG ----------------
OPENAI_CONFIG = {
    "api_key": "sk-Z6rAzMELcOVJO0T9FjLjZw",   # replace with your key
    "base_url": "https://apidev.navigatelabsai.com",
    "embedding_model": "text-embedding-3-small"
}

PCA_MODEL_PATH = "/Users/antojonith/Desktop/JurisRag/pca_model.pkl"
TARGET_DIM = 1024

# --- Clients ---
client = OpenAI(api_key=OPENAI_CONFIG["api_key"], base_url=OPENAI_CONFIG["base_url"])
es = Elasticsearch("http://localhost:9200")
pc = Pinecone(api_key="pcsk_73v1tq_Tpx4n4VnxbDJpYb51DhSBheKssEpM9VyPoLT6imQb7C7kwkVMSUQckjtJgLTXAC")  
index = pc.Index("jurisrag-legal")

# --- Load pretrained PCA model ---
with open(PCA_MODEL_PATH, "rb") as f:
    pca = pickle.load(f)

# --- Embedding Function ---
def get_embedding(text):
    """Generate embedding, reduce with PCA, then zero-pad to Pinecone dim (1024)."""
    resp = client.embeddings.create(input=text, model=OPENAI_CONFIG["embedding_model"])
    vec = np.array(resp.data[0].embedding, dtype=np.float32).reshape(1, -1)

    reduced = pca.transform(vec)   # e.g., 221D
    if reduced.shape[1] < TARGET_DIM:
        padding = np.zeros((1, TARGET_DIM - reduced.shape[1]))
        reduced = np.hstack([reduced, padding])  # → 1024D

    return reduced[0].tolist()

# --- Hybrid Retrieval ---
def hybrid_retrieve(query, top_k=5):
    vector = get_embedding(query)

    # Pinecone semantic
    pinecone_res = index.query(vector=vector, top_k=top_k, include_metadata=True)
    # ES keyword
    es_res = es.search(index="jurisrag-legal", q=query, size=top_k)

    results = []
    for match in pinecone_res["matches"]:
        results.append({
            "id": match["id"],
            "score": match["score"],
            "source": "pinecone",
            "text": match["metadata"]["text"]
        })
    for hit in es_res["hits"]["hits"]:
        results.append({
            "id": hit["_id"],
            "score": hit["_score"],
            "source": "elasticsearch",
            "text": hit["_source"]["text"]
        })

    return results
