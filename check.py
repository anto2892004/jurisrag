import sys
import os
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import OPENAI_CONFIG
import openai

client = openai.OpenAI(
    api_key=OPENAI_CONFIG["api_key"],
    base_url=OPENAI_CONFIG["base_url"]
)

def get_embedding(text):
    if not text.strip():
        return []
    response = client.embeddings.create(
        model=OPENAI_CONFIG["embedding_model"],
        input=text
    )
    return response.data[0].embedding

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def test_basic_embedding():
    text = "The Supreme Court ruled on arbitration clause validity in commercial contracts."
    embedding = get_embedding(text)
    print("✅ Test 1 Passed - Basic embedding")
    print(f"Vector length: {len(embedding)}")
    print(f"Preview: {embedding[:5]}")

def test_empty_text():
    text = "   "
    embedding = get_embedding(text)
    assert embedding == [], "Empty input should return empty embedding"
    print("✅ Test 2 Passed - Empty string handled correctly")

def test_legal_similarity():
    query = "Contract arbitration dispute resolution"
    similar_doc = "Commercial arbitration clause enforcement"
    different_doc = "Criminal procedure evidence requirements"
    emb_query = get_embedding(query)
    emb_similar = get_embedding(similar_doc)
    emb_different = get_embedding(different_doc)
    sim_score = cosine_similarity(emb_query, emb_similar)
    diff_score = cosine_similarity(emb_query, emb_different)
    assert sim_score > diff_score, "Similar concepts should have higher similarity"
    print("✅ Test 3 Passed - Legal similarity detection")
    print(f"Similar score: {sim_score:.4f}, Different score: {diff_score:.4f}")

def test_long_legal_text():
    text = ("The appellant filed a writ petition under Article 226 of the Constitution " +
            "challenging the validity of the government order. The High Court examined " +
            "the procedural compliance and substantive merits of the case. ") * 5
    embedding = get_embedding(text)
    print("✅ Test 4 Passed - Long legal text handled")
    print(f"Vector length: {len(embedding)}")

if __name__ == "__main__":
    print("🔍 Testing text-embedding-3-small for JurisRAG...")
    print("=" * 50)
    try:
        test_basic_embedding()
        test_empty_text()
        test_legal_similarity()
        test_long_legal_text()
        print("=" * 50)
        print("✅ All tests passed! Embedding model ready for JurisRAG.")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print("Check your config.py and API connection.")
