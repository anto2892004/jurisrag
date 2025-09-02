# es_setup.py
from elasticsearch import Elasticsearch, helpers
import json

# Config
ELASTICSEARCH_CONFIG = {
    "host": "http://localhost:9200",
    "index_name": "jurisrag-legal"
}

CHUNKS_FILE = "/Users/antojonith/Desktop/JurisRag/data/processed/enhanced_chunks.jsonl"

# Connect to ES
es = Elasticsearch(ELASTICSEARCH_CONFIG["host"])

# 1. Create Index with Mapping
if es.indices.exists(index=ELASTICSEARCH_CONFIG["index_name"]):
    print("⚠️ Index already exists, deleting...")
    es.indices.delete(index=ELASTICSEARCH_CONFIG["index_name"])

mapping = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
    },
    "mappings": {
        "properties": {
            "case_id": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
            "court": {"type": "keyword"},
            "jurisdiction": {"type": "keyword"},
            "outcome": {"type": "keyword"},
            "statutes": {"type": "keyword"},
            "text": {"type": "text"}
        }
    }
}

es.indices.create(index=ELASTICSEARCH_CONFIG["index_name"], body=mapping)
print("✅ Index created:", ELASTICSEARCH_CONFIG["index_name"])

# 2. Bulk Insert Chunks
actions = []
with open(CHUNKS_FILE, "r") as f:
    for line in f:
        record = json.loads(line)
        actions.append({
            "_index": ELASTICSEARCH_CONFIG["index_name"],
            "_id": record["chunk_id"],
            "_source": record
        })

helpers.bulk(es, actions)
print(f"✅ Inserted {len(actions)} documents into Elasticsearch")
