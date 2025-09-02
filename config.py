import os
from pathlib import Path

OPENAI_CONFIG = {
    "api_key": "sk-Z6rAzMELcOVJO0T9FjLjZw",
    "base_url": "https://apidev.navigatelabsai.com",
    "embedding_model": "text-embedding-3-small",
    "chat_model": "gpt-4.1-nano",
    "embedding_dimensions": 1536,
    "max_tokens": 4096,
    "temperature": 0.1
}

DATA_PATHS = {
    "raw_pdfs": "data/raw_pdfs",
    "processed_cases": "data/processed/cases.jsonl",
    "processed_chunks": "data/processed/chunks.jsonl",
    "enhanced_cases": "data/processed/enhanced_cases.jsonl",
    "enhanced_chunks": "data/processed/enhanced_chunks.jsonl",
    "embeddings": "data/embeddings/",
    "logs": "logs/"
}

VECTOR_DB_CONFIG = {
    "chunk_size": 4000,
    "chunk_overlap": 400,
    "batch_size": 100,
    "similarity_threshold": 0.7,
    "max_results": 10
}

ELASTICSEARCH_CONFIG = {
    "host": "localhost",
    "port": 9200,
    "index_name": "jurisrag-legal",
    "number_of_shards": 1,
    "number_of_replicas": 0
}

PINECONE_CONFIG = {
    "api_key": "pcsk_73v1tq_Tpx4n4VnxbDJpYb51DhSBheKssEpM9VyPoLT6imQb7C7kwkVMSUQckjtJgLTXAC",
    "environment": "us-east-1",
    "index_name": "jurisrag-legal",
    "metric": "cosine"
}

LEGAL_CONFIG = {
    "supported_jurisdictions": [
        "supreme_court", "high_court", "district_court",
        "civil", "criminal", "constitutional", "revenue"
    ],
    "citation_formats": ["AIR", "SCR", "SCC", "All ER"],
    "max_context_chunks": 5,
    "response_max_length": 1000
}

AGENT_CONFIG = {
    "intent_classification_threshold": 0.8,
    "sql_generation_model": "gpt-4.1-nano",
    "judge_model": "gpt-4.1-nano",
    "max_retrieval_attempts": 3,
    "response_timeout": 30
}

def setup_directories():
    for path in DATA_PATHS.values():
        if path.endswith('/'):
            Path(path).mkdir(parents=True, exist_ok=True)
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    print("Directory structure created successfully!")

if __name__ == "__main__":
    setup_directories()
