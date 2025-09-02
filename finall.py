import json
import re
import sqlite3
import time
import random
from openai import OpenAI
from elasticsearch import Elasticsearch
from pinecone import Pinecone
import numpy as np
from sklearn.decomposition import PCA

# ---------------- CONFIG ----------------
OPENAI_CONFIG = {
    "api_key": "sk-Z6rAzMELcOVJO0T9FjLjZw",   # replace with your key
    "base_url": "https://apidev.navigatelabsai.com",
    "embedding_model": "text-embedding-3-small",
    "judge_model": "gpt-4.1-nano",
    "generator_models": ["llama3-8b-8192", "nova-micro", "gemini-2.5-flash"]
}

DB_PATH = "/Users/antojonith/Desktop/JurisRag/data/jurisrag.db"
TABLE_NAME = "chunks"

ALLOWED_COLUMNS = {
    "chunk_id","case_id","case_number","file_name","year","courts",
    "jurisdiction","statutes","reliefs","outcomes","legal_concepts","text"
}

# --- OpenAI client ---
client = OpenAI(api_key=OPENAI_CONFIG["api_key"], base_url=OPENAI_CONFIG["base_url"])

# --- ES client ---
es = Elasticsearch("http://localhost:9200")

# --- Pinecone client ---
pc = Pinecone(api_key="pcsk_73v1tq_Tpx4n4VnxbDJpYb51DhSBheKssEpM9VyPoLT6imQb7C7kwkVMSUQckjtJgLTXAC")  # replace with your Pinecone key
index = pc.Index("jurisrag-legal")

# --- Embeddings with PCA (to 1024D) ---
def get_embedding(text):
    resp = client.embeddings.create(input=text, model=OPENAI_CONFIG["embedding_model"])
    vec = np.array(resp.data[0].embedding, dtype=np.float32).reshape(1, -1)
    pca = PCA(n_components=1024)
    return pca.fit_transform(vec)[0].tolist()

# --- Hybrid retrieval ---
def hybrid_retrieve(query, top_k=5):
    vector = get_embedding(query)

    pinecone_res = index.query(vector=vector, top_k=top_k, include_metadata=True)
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

# --- SQL query generator (simplified for demo) ---
SYSTEM_PROMPT = f"""
You are a SQL generator. Convert plain English legal questions into a single safe SQLite SELECT statement.
Use only table '{TABLE_NAME}' with columns: {', '.join(sorted(ALLOWED_COLUMNS))}.
Return only the SQL SELECT (no explanation, no semicolon).
"""

def ask_llm_for_sql(question):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {question}"}
    ]
    resp = client.chat.completions.create(
        model=OPENAI_CONFIG["judge_model"],  # small model to generate SQL
        messages=messages,
        max_tokens=100
    )
    sql = resp.choices[0].message.content.strip()
    sql = re.sub(r"```sql|```", "", sql).strip().rstrip(";")
    return sql

def execute_sql(sql):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    result = [dict(zip(cols, r)) for r in rows]
    conn.close()
    return {"columns": cols, "rows": result}

# --- Multi-model generation ---
def generate_with_model(model, query, context, sql_results):
    messages = [
        {"role": "system", "content": "You are a helpful legal assistant."},
        {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}\n\nStructured Data:\n{json.dumps(sql_results, indent=2)}"}
    ]
    resp = client.chat.completions.create(model=model, messages=messages, max_tokens=500)
    return resp.choices[0].message.content.strip()

def judge_answers(query, context, sql_results, answers):
    judge_prompt = f"""
You are a judge. The user asked: {query}

Context:
{context}

SQL Results:
{json.dumps(sql_results, indent=2)}

Candidate Answers:
{json.dumps(answers, indent=2)}

Task: Pick the best answer (accurate, clear, faithful). Merge if useful.
Return only the final answer.
"""
    resp = client.chat.completions.create(
        model=OPENAI_CONFIG["judge_model"],
        messages=[{"role": "system", "content": "You are a fair evaluator."},
                  {"role": "user", "content": judge_prompt}],
        max_tokens=400
    )
    return resp.choices[0].message.content.strip()

# --- Full pipeline ---
def pipeline(query):
    print(f"\n🔎 Query: {query}")

    # 1. Hybrid retrieval
    retrieved = hybrid_retrieve(query)
    context = "\n\n".join([doc["text"][:400] for doc in retrieved])

    # 2. SQL
    sql = ask_llm_for_sql(query)
    sql_results = execute_sql(sql)

    # 3. Candidate answers
    answers = {}
    for model in OPENAI_CONFIG["generator_models"]:
        try:
            answers[model] = generate_with_model(model, query, context, sql_results)
        except Exception as e:
            answers[model] = f"[Error from {model}: {e}]"

    # 4. Judge
    final = judge_answers(query, context, sql_results, answers)

    print("\n✅ Final Answer:\n", final)
    return final


if __name__ == "__main__":
    pipeline("Explain arbitration principles in Indian law between 1950 and 1960")
