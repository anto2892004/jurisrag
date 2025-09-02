import os
import sys
import json
import numpy as np
from tqdm import tqdm
import traceback
import pickle
from sklearn.decomposition import PCA

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import OPENAI_CONFIG
from test_models.test_embedding import get_embedding  # reuse tested embedding fn

# Input & Output Paths
CHUNKS_FILE = "/Users/antojonith/Desktop/JurisRag/data/processed/enhanced_chunks.jsonl"
PCA_MODEL_FILE = "/Users/antojonith/Desktop/JurisRag/pca_model.pkl"
EMBEDDINGS_JSON = "/Users/antojonith/Desktop/JurisRag/data/processed/embeddings_pca.jsonl"
EMBEDDINGS_NPY = "/Users/antojonith/Desktop/JurisRag/data/processed/embeddings_pca.npy"

TARGET_DIM = 1024   # Pinecone requires 1024

def generate_raw_embeddings():
    """Step 1: Generate raw 1536-d embeddings"""
    embeddings = []
    metadata_list = []

    with open(CHUNKS_FILE, "r") as infile:
        for line in tqdm(infile, desc="Generating raw embeddings"):
            try:
                chunk = json.loads(line)
                text = chunk.get("text", "").strip()

                if not text:
                    continue

                embedding = get_embedding(text)
                embeddings.append(embedding)

                metadata_list.append({
                    "case_id": chunk.get("case_id"),
                    "chunk_id": chunk.get("chunk_id"),
                    "text": text,
                    "court": chunk.get("court"),
                    "jurisdiction": chunk.get("jurisdiction"),
                    "statutes": chunk.get("statutes"),
                    "outcome": chunk.get("outcome")
                })

            except Exception as e:
                print("⚠️ Error embedding chunk:", str(e))
                traceback.print_exc()
                continue

    return np.array(embeddings, dtype=np.float32), metadata_list


def train_pca(embeddings, target_dim=TARGET_DIM):
    """Step 2: Train PCA to reduce embeddings and pad to target_dim"""
    max_components = min(embeddings.shape[0], embeddings.shape[1])

    if target_dim > max_components:
        print(f"⚠️ Cannot train PCA with {target_dim} components. Using {max_components} instead.")
        n_components = max_components
    else:
        n_components = target_dim

    print(f"🔍 Training PCA to reduce {embeddings.shape[1]} → {n_components}")
    pca = PCA(n_components=n_components, random_state=42)
    reduced = pca.fit_transform(embeddings)

    # Zero-pad if reduced < target_dim
    if reduced.shape[1] < target_dim:
        padding = np.zeros((reduced.shape[0], target_dim - reduced.shape[1]))
        reduced = np.hstack([reduced, padding])
        print(f"ℹ️ Zero-padded from {n_components} → {target_dim}")

    # Save PCA model
    with open(PCA_MODEL_FILE, "wb") as f:
        pickle.dump(pca, f)
    print(f"✅ PCA model saved at {PCA_MODEL_FILE}")

    return reduced


def save_reduced_embeddings(reduced_embeddings, metadata_list):
    """Step 3: Save reduced embeddings in JSONL and NPY"""
    with open(EMBEDDINGS_JSON, "w") as out_json:
        for vec, meta in zip(reduced_embeddings, metadata_list):
            record = {
                **meta,
                "embedding": vec.tolist()
            }
            out_json.write(json.dumps(record) + "\n")

    np.save(EMBEDDINGS_NPY, reduced_embeddings.astype(np.float32))
    print(f"✅ Saved {len(reduced_embeddings)} reduced embeddings:")
    print(f"   - JSONL: {EMBEDDINGS_JSON}")
    print(f"   - NPY:   {EMBEDDINGS_NPY}")


# 🔹 Helper for new queries
def get_reduced_embedding(text: str):
    """Generate 1536-d embedding → PCA reduce → zero-pad → 1024-d"""
    if not text.strip():
        return np.zeros(TARGET_DIM, dtype=np.float32)

    # Load PCA model
    with open(PCA_MODEL_FILE, "rb") as f:
        pca = pickle.load(f)

    raw_emb = get_embedding(text)  # 1536-d
    raw_emb = np.array(raw_emb).reshape(1, -1)

    reduced = pca.transform(raw_emb)  # may be < 1024
    if reduced.shape[1] < TARGET_DIM:
        padding = np.zeros((1, TARGET_DIM - reduced.shape[1]))
        reduced = np.hstack([reduced, padding])

    return reduced.flatten().astype(np.float32)


if __name__ == "__main__":
    # Step 1: Generate embeddings
    raw_embeddings, metadata = generate_raw_embeddings()

    # Step 2: Train PCA & reduce
    reduced_embeddings = train_pca(raw_embeddings, TARGET_DIM)

    # Step 3: Save reduced embeddings
    save_reduced_embeddings(reduced_embeddings, metadata)
