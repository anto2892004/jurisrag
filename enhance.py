import re
import json
from pathlib import Path

COURT_PATTERNS = [
    re.compile(r'(Supreme Court of India|High Court|District Court|Sessions Court|Magistrate Court)', re.I),
    re.compile(r'(Calcutta High Court|Bombay High Court|Delhi High Court|Madras High Court)', re.I),
    re.compile(r'Court of ([A-Za-z\s]+)', re.I)
]

JURISDICTION_PATTERNS = [
    re.compile(r'(Civil|Criminal|Constitutional|Revenue|Commercial|Family|Labour)', re.I),
    re.compile(r'(Appeal|Revision|Writ|Original)', re.I)
]

STATUTE_PATTERNS = [
    re.compile(r'(Indian Penal Code|Code of Civil Procedure|Code of Criminal Procedure|Evidence Act|Contract Act|Companies Act)', re.I),
    re.compile(r'(Section\s+\d+[A-Z]*|Article\s+\d+|Rule\s+\d+)', re.I),
    re.compile(r'(I\.P\.C\.|Cr\.P\.C\.|C\.P\.C\.|I\.E\.A\.)', re.I)
]

RELIEF_PATTERNS = [
    re.compile(r'(injunction|damages|compensation|specific performance|declaration|mandamus|certiorari|prohibition)', re.I),
    re.compile(r'(relief|remedy|order|direction|decree)', re.I)
]

OUTCOME_PATTERNS = [
    re.compile(r'(allowed|dismissed|partly allowed|remanded|set aside|affirmed|reversed)', re.I),
    re.compile(r'(appeal\s+(allowed|dismissed)|petition\s+(allowed|dismissed))', re.I),
    re.compile(r'(decree\s+(passed|dismissed)|suit\s+(decreed|dismissed))', re.I)
]

def extract_enhanced_metadata(text, basic_metadata):
    enhanced = basic_metadata.copy()
    courts = []
    for pattern in COURT_PATTERNS:
        matches = pattern.findall(text[:3000])
        courts.extend([match.strip() for match in matches if isinstance(match, str)])
        courts.extend([m for match in matches if isinstance(match, tuple) for m in match if m.strip()])
    enhanced['courts'] = list(set(courts[:3]))
    jurisdictions = []
    for pattern in JURISDICTION_PATTERNS:
        matches = pattern.findall(text[:2000])
        jurisdictions.extend([match.strip() for match in matches if isinstance(match, str)])
        jurisdictions.extend([m for match in matches if isinstance(match, tuple) for m in match if m.strip()])
    enhanced['jurisdiction'] = list(set(jurisdictions[:3]))
    statutes = []
    for pattern in STATUTE_PATTERNS:
        matches = pattern.findall(text)
        statutes.extend([match.strip() for match in matches if isinstance(match, str)])
        statutes.extend([m for match in matches if isinstance(match, tuple) for m in match if m.strip()])
    enhanced['statutes'] = list(set(statutes[:5]))
    reliefs = []
    for pattern in RELIEF_PATTERNS:
        matches = pattern.findall(text)
        reliefs.extend([match.strip().lower() for match in matches if isinstance(match, str)])
        reliefs.extend([m.strip().lower() for match in matches if isinstance(match, tuple) for m in match if m.strip()])
    enhanced['reliefs'] = list(set(reliefs[:3]))
    outcomes = []
    for pattern in OUTCOME_PATTERNS:
        matches = pattern.findall(text[-2000:])
        outcomes.extend([match.strip().lower() for match in matches if isinstance(match, str)])
        outcomes.extend([m.strip().lower() for match in matches if isinstance(match, tuple) for m in match if m.strip()])
    enhanced['outcomes'] = list(set(outcomes[:3]))
    legal_concepts = []
    concept_patterns = [
        r'principle of natural justice', r'burden of proof', r'res judicata',
        r'estoppel', r'locus standi', r'ultra vires', r'mala fide', r'bona fide',
        r'arbitration', r'mediation', r'specific performance', r'breach of contract'
    ]
    for concept in concept_patterns:
        if re.search(concept, text, re.I):
            legal_concepts.append(concept)
    enhanced['legal_concepts'] = legal_concepts[:5]
    return enhanced

def enhance_existing_data(cases_file, chunks_file, output_cases_file, output_chunks_file):
    enhanced_cases = []
    enhanced_chunks = []
    print("Enhancing cases...")
    with open(cases_file, 'r', encoding='utf-8') as f:
        for line in f:
            case = json.loads(line.strip())
            enhanced_case = extract_enhanced_metadata(case['text'], case)
            enhanced_cases.append(enhanced_case)
    print("Enhancing chunks...")
    with open(chunks_file, 'r', encoding='utf-8') as f:
        for line in f:
            chunk = json.loads(line.strip())
            case_data = next((c for c in enhanced_cases if c['case_id'] == chunk['case_id']), None)
            if case_data:
                chunk['courts'] = case_data.get('courts', [])
                chunk['jurisdiction'] = case_data.get('jurisdiction', [])
                chunk['statutes'] = case_data.get('statutes', [])
                chunk['reliefs'] = case_data.get('reliefs', [])
                chunk['outcomes'] = case_data.get('outcomes', [])
                chunk['legal_concepts'] = case_data.get('legal_concepts', [])
            enhanced_chunks.append(chunk)
    with open(output_cases_file, 'w', encoding='utf-8') as f:
        for case in enhanced_cases:
            f.write(json.dumps(case, ensure_ascii=False) + '\n')
    with open(output_chunks_file, 'w', encoding='utf-8') as f:
        for chunk in enhanced_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    print(f"Enhanced {len(enhanced_cases)} cases and {len(enhanced_chunks)} chunks")
    print(f"Output: {output_cases_file}, {output_chunks_file}")

if __name__ == "__main__":
    enhance_existing_data(
        'data/processed/cases.jsonl',
        'data/processed/chunks.jsonl',
        'data/processed/enhanced_cases.jsonl',
        'data/processed/enhanced_chunks.jsonl'
    )
