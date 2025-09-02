import os
import sys
import json
import uuid
from tqdm import tqdm
from pinecone import Pinecone, ServerlessSpec

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import PINECONE_CONFIG
from generate_embedding import get_reduced_embedding  # helper for queries later

# Paths
EMBEDDINGS_JSON = "/Users/antojonith/Desktop/JurisRag/data/processed/embeddings_pca.jsonl"

# ---------------------------
# 1. Init Pinecone Client
# ---------------------------
pc = Pinecone(api_key=PINECONE_CONFIG["api_key"])
index_name = PINECONE_CONFIG["index_name"]

# Create index if it doesn’t exist
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1024,  # reduced dim
        metric=PINECONE_CONFIG.get("metric", "cosine"),
        spec=ServerlessSpec(cloud="aws", region=PINECONE_CONFIG.get("environment", "us-east-1"))
    )

index = pc.Index(index_name)

# ---------------------------
# 2. Load Reduced Embeddings
# ---------------------------
def load_embeddings(file_path):
    with open(file_path, "r") as f:
        for line in f:
            yield json.loads(line)

# ---------------------------
# Helper: Sanitize Metadata
# ---------------------------
def sanitize_metadata(record):
    metadata = {
        "case_id": record.get("case_id") or "",
        "chunk_id": record.get("chunk_id") or "",
        "court": record.get("court") or "",
        "jurisdiction": record.get("jurisdiction") or "",
        "statutes": record.get("statutes") or [],
        "outcome": record.get("outcome") or "",
        "text": record.get("text") or ""
    }

    # Ensure statutes is list of strings
    if not isinstance(metadata["statutes"], list):
        metadata["statutes"] = [str(metadata["statutes"])] if metadata["statutes"] else []

    return metadata

# ---------------------------
# 3. Upsert to Pinecone
# ---------------------------
def upsert_embeddings():
    batch = []
    batch_size = 50

    for record in tqdm(load_embeddings(EMBEDDINGS_JSON), desc="Uploading to Pinecone"):
        vector_id = str(uuid.uuid4())  # unique id
        embedding = record["embedding"]
        metadata = sanitize_metadata(record)

        batch.append({"id": vector_id, "values": embedding, "metadata": metadata})

        # Upload in batches
        if len(batch) >= batch_size:
            index.upsert(vectors=batch)
            batch = []

    if batch:
        index.upsert(vectors=batch)

    print("✅ All embeddings stored in Pinecone!")

# ---------------------------
# 4. Test Query
# ---------------------------
def test_query():
    query = "Arbitration clause validity in contracts"
    query_embedding = get_reduced_embedding(query)

    results = index.query(vector=query_embedding.tolist(), top_k=5, include_metadata=True)
    print("\n🔍 Sample Query Results:")
    for match in results["matches"]:
        print(f"Score: {match['score']:.4f}")
        print(f"Text: {match['metadata'].get('text')[:200]}...\n")


if __name__ == "__main__":
    upsert_embeddings()
    test_query()
