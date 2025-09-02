import json
from collections import Counter
import pandas as pd

def inspect_enhanced_data(cases_file, chunks_file):
    """Inspect the quality of enhanced metadata"""
    
    cases = []
    chunks = []
    
    # Load data
    with open(cases_file, 'r', encoding='utf-8') as f:
        for line in f:
            cases.append(json.loads(line.strip()))
    
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line.strip()))
    
    print("=== DATA QUALITY INSPECTION ===")
    print(f"Total Cases: {len(cases)}")
    print(f"Total Chunks: {len(chunks)}")
    print()
    
    # Analyze metadata coverage
    print("=== METADATA COVERAGE ===")
    metadata_fields = ['courts', 'jurisdiction', 'statutes', 'reliefs', 'outcomes', 'legal_concepts']
    
    for field in metadata_fields:
        non_empty = sum(1 for case in cases if case.get(field) and len(case.get(field, [])) > 0)
        coverage = (non_empty / len(cases)) * 100
        print(f"{field.capitalize()}: {non_empty}/{len(cases)} cases ({coverage:.1f}%)")
    
    print()
    
    # Show sample enhanced case
    print("=== SAMPLE ENHANCED CASE ===")
    sample_case = cases[0]
    print(f"Case ID: {sample_case['case_id']}")
    print(f"Year: {sample_case['year']}")
    print(f"Courts: {sample_case.get('courts', [])}")
    print(f"Jurisdiction: {sample_case.get('jurisdiction', [])}")
    print(f"Statutes: {sample_case.get('statutes', [])[:3]}...")  # First 3
    print(f"Reliefs: {sample_case.get('reliefs', [])}")
    print(f"Outcomes: {sample_case.get('outcomes', [])}")
    print(f"Legal Concepts: {sample_case.get('legal_concepts', [])}")
    print()
    
    # Analyze most common metadata values
    print("=== MOST COMMON VALUES ===")
    
    all_courts = []
    all_jurisdictions = []
    all_statutes = []
    all_concepts = []
    
    for case in cases:
        all_courts.extend(case.get('courts', []))
        all_jurisdictions.extend(case.get('jurisdiction', []))
        all_statutes.extend(case.get('statutes', []))
        all_concepts.extend(case.get('legal_concepts', []))
    
    print("Top Courts:")
    for court, count in Counter(all_courts).most_common(5):
        print(f"  {court}: {count}")
    
    print("\nTop Jurisdictions:")
    for juris, count in Counter(all_jurisdictions).most_common(5):
        print(f"  {juris}: {count}")
    
    print("\nTop Statutes:")
    for statute, count in Counter(all_statutes).most_common(5):
        print(f"  {statute}: {count}")
    
    print("\nTop Legal Concepts:")
    for concept, count in Counter(all_concepts).most_common(5):
        print(f"  {concept}: {count}")
    
    print()
    
    # Check chunk distribution
    chunks_per_case = Counter(chunk['case_id'] for chunk in chunks)
    avg_chunks = sum(chunks_per_case.values()) / len(chunks_per_case)
    print(f"=== CHUNKING ANALYSIS ===")
    print(f"Average chunks per case: {avg_chunks:.1f}")
    print(f"Min chunks: {min(chunks_per_case.values())}")
    print(f"Max chunks: {max(chunks_per_case.values())}")
    
    # Sample chunk
    print("\n=== SAMPLE CHUNK ===")
    sample_chunk = chunks[0]
    print(f"Chunk ID: {sample_chunk['chunk_id']}")
    print(f"Case ID: {sample_chunk['case_id']}")
    print(f"Courts: {sample_chunk.get('courts', [])}")
    print(f"Text preview: {sample_chunk['text'][:200]}...")
    
    return cases, chunks

if __name__ == "__main__":
    cases, chunks = inspect_enhanced_data(
        'data/processed/enhanced_cases.jsonl',
        'data/processed/enhanced_chunks.jsonl'
    )