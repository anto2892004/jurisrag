import re
import sqlite3
import json
import time
import random
from openai import OpenAI
from pathlib import Path

OPENAI_CONFIG = {
    "api_key": "sk-Z6rAzMELcOVJO0T9FjLjZw",
    "base_url": "https://apidev.navigatelabsai.com",
    "llm_model": "gpt-4.1-nano"
}

DB_PATH = "/Users/antojonith/Desktop/JurisRag/data/jurisrag.db"

TABLE_NAME = "chunks"
ALLOWED_COLUMNS = {
    "chunk_id","case_id","case_number","file_name","year","courts",
    "jurisdiction","statutes","reliefs","outcomes","legal_concepts","text"
}

FORBIDDEN_KEYWORDS = {
    "insert","update","delete","drop","create","alter","attach","detach",
    "pragma","replace","vacuum","merge","exec","begin","commit","rollback"
}

client = OpenAI(api_key=OPENAI_CONFIG["api_key"], base_url=OPENAI_CONFIG["base_url"])

SYSTEM_PROMPT = f"""
You are a careful assistant that converts plain English legal questions into a single, safe SQLite SELECT statement.
Use only the table named '{TABLE_NAME}' and only these columns: {', '.join(sorted(ALLOWED_COLUMNS))}.
Return only a single SELECT statement (SQLite dialect). Use COUNT, SUM, AVG, GROUP BY when appropriate.
Use LIKE for substring/statute matching and BETWEEN for ranges.
If counting cases, prefer COUNT(DISTINCT case_id).
Do NOT return any DDL or DML (no CREATE/INSERT/UPDATE/DELETE/DROP). Do not use semicolons, and do not include explanation — only return the SQL.
"""

def ask_llm_for_sql(nl_question, max_attempts=3):
    base_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {nl_question}\n\nSchema: Table {TABLE_NAME} with columns {', '.join(sorted(ALLOWED_COLUMNS))}.\n\nReturn only the SQL SELECT statement."}
    ]
    delay = 2
    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.chat.completions.create(
                model=OPENAI_CONFIG["llm_model"],
                messages=base_messages,
                max_tokens=100,
                timeout=30
            )
            text = resp.choices[0].message.content.strip()
            m = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.S)
            sql = m.group(1).strip() if m else text
            sql = sql.strip().rstrip(";")
            if validate_sql(sql):
                return sql
            else:
                print(f"⚠️ Attempt {attempt}: invalid SQL returned -> {sql}")
        except Exception as e:
            print(f"⚠️ Attempt {attempt}: API error -> {e}")
        sleep_for = delay + random.uniform(0, 1)
        print(f"⏳ Sleeping {sleep_for:.1f}s before retry...")
        time.sleep(sleep_for)
        delay = min(delay * 2, 60)
    raise ValueError("LLM failed to produce valid SQL after retries")

def validate_sql(sql_text):
    s = sql_text.strip().lower()
    if not s.startswith("select"):
        return False
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", s):
            return False
    if ";" in sql_text:
        return False
    if re.search(r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", s):
        table = re.search(r"\bfrom\s+([a-zA-Z_][a-zA-Z0-9_]*)\b", s).group(1)
        if table != TABLE_NAME:
            return False
    else:
        return False
    select_clause = re.search(r"select\s+(.*?)\s+from\s", s, flags=re.S)
    if select_clause:
        cols = select_clause.group(1)
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", cols)
        SQL_KEYWORDS = {"select","from","where","group","by","order","count","distinct","sum","avg","min","max","as"}
        for t in tokens:
            if t.lower() in SQL_KEYWORDS:
                continue
            if t.lower() not in {c.lower() for c in ALLOWED_COLUMNS}:
                return False
    return True

def execute_sql(sql_text):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql_text)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    result = [dict(zip(cols, r)) for r in rows]
    conn.close()
    return {"columns": cols, "rows": result}

def ask_and_run(nl_question):
    print("🔎 Natural language:", nl_question)
    sql = ask_llm_for_sql(nl_question)
    print("✅ Generated SQL:", sql)
    results = execute_sql(sql)
    print("✅ SQL executed, rows:", len(results["rows"]))
    if len(results["rows"]) <= 50:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    time.sleep(random.uniform(1, 2))
    return results

if __name__ == "__main__":
    examples = [
        "How many cases mention arbitration between 1950 and 1960?",
        "Number of cases in Calcutta High Court about 'arbitration' between 1945 and 1955",
        "Show the count of cases per year that contain the word 'arbitration' between 1950 and 1960",
        "List case_id and file_name where statutes mention section 109"
    ]
    for q in examples:
        try:
            r = ask_and_run(q)
        except Exception as e:
            print("❌ Error:", str(e))
