import os, json, re, argparse, gc
from pathlib import Path
from tqdm import tqdm
import fitz    # pymupdf
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

# ------- helpers -------
def clean_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

YEAR_RE = re.compile(r'(\b19\d{2}\b|\b20\d{2}\b)')
CASE_NUM_RE = re.compile(r'(CIVIL|CRIMINAL|SPECIAL LEAVE|S.L.P|C\.A\.|CIVIL APPEAL|CRL)\b.*?NO[.:]?\s*[\w\-/\s\d,]+', re.I)
PARTIES_RE = re.compile(r'([A-Z][A-Za-z\.\-&\s]{2,80})\s+(?:v(?:s|ersus|\.s\.?)|versus|vs\.?)\s+([A-Z][A-Za-z\.\-&\s]{2,80})', re.I)
DATE_RE1 = re.compile(r'(\d{1,2}\s+(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\s+\d{4})', re.I)
DATE_RE2 = re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})')

def extract_metadata_from_text(text, filename, year_from_folder):
    meta = {}
    meta['file_name'] = filename
    # year: prefer folder year, then detect in text
    meta['year'] = year_from_folder or (YEAR_RE.search(text).group(1) if YEAR_RE.search(text) else "unknown")
    # case number
    cm = CASE_NUM_RE.search(text)
    meta['case_number'] = cm.group(0).strip() if cm else "unknown"
    # parties
    pm = PARTIES_RE.search(text[:2000])  # search in top 2k chars
    if pm:
        meta['party_1'] = pm.group(1).strip()
        meta['party_2'] = pm.group(2).strip()
    else:
        meta['party_1'] = meta['party_2'] = "unknown"
    # date
    dm = DATE_RE1.search(text) or DATE_RE2.search(text)
    meta['decision_date'] = dm.group(1) if dm else "unknown"
    # judges (naive: near "J." or "JUDGMENT" header)
    jm = re.search(r'(JUDGMENT|J U D G M E N T|Coram:|Before:|J\.)\s*(.*?)(?=\n)', text[:2000], re.I)
    meta['judges'] = (jm.group(2).strip() if jm else "unknown")
    return meta

def chunk_text(text, chunk_size=4000, overlap=400):
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(L, start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
        start = end - overlap
        if start <= 0 or start >= L - overlap:
            break
    return chunks

def process_pdf(args_tuple):
    """Process a single PDF - now takes a tuple to work with ThreadPoolExecutor"""
    path, idx, year_folder = args_tuple
    
    try:
        # Open document with explicit memory management
        doc = fitz.open(str(path))
        
        # Process pages one by one to reduce memory usage
        full_text_parts = []
        page_count = doc.page_count
        
        # Limit pages if document is very large
        max_pages = min(page_count, 1000)  # Limit to 1000 pages to prevent memory issues
        
        for page_num in range(max_pages):
            try:
                page = doc[page_num]
                page_text = page.get_text("text")
                if page_text and page_text.strip():
                    full_text_parts.append(page_text)
                # Clean up page object
                del page
            except Exception as e:
                print(f"Error processing page {page_num} in {path.name}: {e}")
                continue
        
        # Close document explicitly
        doc.close()
        del doc
        
        # Join and clean text
        text = "\n".join(full_text_parts)
        del full_text_parts  # Free memory
        
        if not text.strip():
            return None, f"empty:{path.name}"
        
        text = clean_text(text)
        
        # Limit text size to prevent memory issues (e.g., max 1MB of text)
        if len(text) > 1_000_000:
            text = text[:1_000_000]
            print(f"Warning: Truncated large document {path.name}")
        
        meta = extract_metadata_from_text(text, path.name, year_folder)
        case_id = f"{year_folder}_{idx:06d}"
        
        case_rec = {
            "case_id": case_id,
            "file_name": path.name,
            "year": meta['year'],
            "case_number": meta['case_number'],
            "party_1": meta['party_1'],
            "party_2": meta['party_2'],
            "decision_date": meta['decision_date'],
            "judges": meta['judges'],
            "text": text
        }
        
        # Create chunks
        chunks = []
        parts = chunk_text(text, chunk_size=4000, overlap=400)
        
        for i, part in enumerate(parts):
            chunks.append({
                "chunk_id": f"{case_id}_chunk_{i:03d}",
                "case_id": case_id,
                "text": part,
                "file_name": path.name,
                "year": meta['year'],
                "case_number": meta['case_number'],
            })
        
        # Force garbage collection
        del text, parts
        gc.collect()
        
        return (case_rec, chunks), None
        
    except Exception as e:
        return None, f"err:{path.name}:{str(e)}"

def write_batch_to_files(batch_results, fc, fch, logf):
    """Write a batch of results to files"""
    for result, error in batch_results:
        if error:
            logf.write(error + "\n")
            logf.flush()
            continue
        
        case_rec, chunks = result
        fc.write(json.dumps(case_rec, ensure_ascii=False) + "\n")
        fc.flush()
        
        for chunk in chunks:
            fch.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        fch.flush()

# ------- main -------
def main(input_dir, out_cases, out_chunks, workers=2, limit=None, batch_size=10):
    input_dir = Path(input_dir)
    all_files = []
    
    # Traverse year folders
    for year_folder in sorted(p.name for p in input_dir.iterdir() if p.is_dir()):
        folder = input_dir / year_folder
        if not folder.exists():
            continue
        
        try:
            files = [folder / f for f in sorted(os.listdir(folder)) if f.lower().endswith(".pdf")]
            for f in files:
                all_files.append((f, year_folder))
        except (OSError, PermissionError) as e:
            print(f"Error accessing folder {folder}: {e}")
            continue
    
    if limit:
        all_files = all_files[:limit]
    
    print(f"Found {len(all_files)} PDF files to process")
    
    # Create argument tuples for processing
    process_args = [(path, idx, year_folder) for idx, (path, year_folder) in enumerate(all_files)]
    
    # Process in batches to manage memory
    total_batches = (len(process_args) + batch_size - 1) // batch_size
    
    with open(out_cases, "w", encoding="utf-8") as fc, \
         open(out_chunks, "w", encoding="utf-8") as fch, \
         open("logs/extract_errors.log", "w", encoding="utf-8") as logf:
        
        processed_count = 0
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(process_args))
            batch_args = process_args[start_idx:end_idx]
            
            print(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch_args)} files)")
            
            # Process current batch
            batch_results = []
            
            with ThreadPoolExecutor(max_workers=min(workers, len(batch_args))) as executor:
                futures = {executor.submit(process_pdf, args): args for args in batch_args}
                
                for future in tqdm(as_completed(futures), 
                                 total=len(futures), 
                                 desc=f"Batch {batch_idx + 1}"):
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per file
                        batch_results.append(result)
                    except Exception as e:
                        args = futures[future]
                        error_msg = f"timeout/error:{args[0].name}:{str(e)}"
                        batch_results.append((None, error_msg))
                    finally:
                        processed_count += 1
            
            # Write batch results
            write_batch_to_files(batch_results, fc, fch, logf)
            
            # Clean up
            del batch_results
            gc.collect()
            
            # Brief pause between batches to allow system to recover
            time.sleep(1)
        
        print(f"Processed {processed_count} files total")

    print("Done. cases ->", out_cases, "chunks ->", out_chunks)
    print("Errors logged at logs/extract_errors.log")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw_pdfs", help="root folder with year subfolders")
    parser.add_argument("--out_cases", default="data/processed/cases.jsonl", help="output cases jsonl")
    parser.add_argument("--out_chunks", default="data/processed/chunks.jsonl", help="output chunks jsonl")
    parser.add_argument("--workers", type=int, default=2, help="number of worker threads (keep low to avoid memory issues)")
    parser.add_argument("--limit", type=int, default=None, help="limit number of files (for testing)")
    parser.add_argument("--batch_size", type=int, default=10, help="number of files to process in each batch")
    args = parser.parse_args()
    
    # Create directories
    os.makedirs(Path(args.out_cases).parent, exist_ok=True)
    os.makedirs(Path(args.out_chunks).parent, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    main(args.input, args.out_cases, args.out_chunks, 
         workers=args.workers, limit=args.limit, batch_size=args.batch_size)