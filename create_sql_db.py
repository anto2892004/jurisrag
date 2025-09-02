# create_sql_db.py
import sqlite3
import json
from tqdm import tqdm
from pathlib import Path

# Paths - adjust if needed
CHUNKS_FILE = "/Users/antojonith/Desktop/JurisRag/data/processed/enhanced_chunks.jsonl"
DB_PATH = "/Users/antojonith/Desktop/JurisRag/data/jurisrag.db"

def list_to_str(v):
    if v is None:
        return ""
    if isinstance(v, list):
        # join lists with a separator that won't appear normally in text
        return " ||| ".join([str(x) for x in v])
    return str(v)

def create_db(path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        chunk_id TEXT PRIMARY KEY,
        case_id TEXT,
        case_number TEXT,
        file_name TEXT,
        year INTEGER,
        courts TEXT,
        jurisdiction TEXT,
        statutes TEXT,
        reliefs TEXT,
        outcomes TEXT,
        legal_concepts TEXT,
        text TEXT
    )
    """)
    # indexes for faster queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_case_id ON chunks(case_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_year ON chunks(year)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_courts ON chunks(courts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_statutes ON chunks(statutes)")
    conn.commit()
    return conn

def load_chunks_into_db(conn, chunks_file):
    cur = conn.cursor()
    count = 0
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="Indexing chunks"):
            if not line.strip():
                continue
            rec = json.loads(line)
            chunk_id = rec.get("chunk_id") or rec.get("id") or ""
            cur.execute("""
                INSERT OR REPLACE INTO chunks
                (chunk_id, case_id, case_number, file_name, year, courts, jurisdiction, statutes, reliefs, outcomes, legal_concepts, text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id,
                rec.get("case_id") or "",
                rec.get("case_number") or "",
                rec.get("file_name") or "",
                int(rec["year"]) if rec.get("year") and str(rec.get("year")).isdigit() else None,
                list_to_str(rec.get("courts")),
                list_to_str(rec.get("jurisdiction")),
                list_to_str(rec.get("statutes")),
                list_to_str(rec.get("reliefs")),
                list_to_str(rec.get("outcomes")),
                list_to_str(rec.get("legal_concepts")),
                rec.get("text") or ""
            ))
            count += 1
    conn.commit()
    print(f"✅ Inserted {count} rows into {DB_PATH}")

if __name__ == "__main__":
    conn = create_db(DB_PATH)
    load_chunks_into_db(conn, CHUNKS_FILE)
    conn.close()
