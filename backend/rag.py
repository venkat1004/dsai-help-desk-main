import os
import re
import numpy as np
import faiss
import docx
from sentence_transformers import SentenceTransformer

# -------- YOUR SINGLE KB FILE --------
KB_FILE = r"C:\Users\venkatsai.reddy\Downloads\KB File List.docx"
# -------------------------------------

model = SentenceTransformer("all-MiniLM-L6-v2")

faiss_index = None
metadata_store = []

# --------- READ DOCX SAFELY ----------
def read_docx_text(path):
    doc = docx.Document(path)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return text
# -------------------------------------

def extract_metadata_from_chunk(chunk):
    meta = {"id": None, "title": None, "version": None}

    id_match = re.search(r"id:\s*(.+)", chunk)
    title_match = re.search(r"title:\s*(.+)", chunk)
    version_match = re.search(r"version:\s*(.+)", chunk)

    if id_match:
        meta["id"] = id_match.group(1).strip()
    if title_match:
        meta["title"] = title_match.group(1).strip()
    if version_match:
        meta["version"] = version_match.group(1).strip()

    return meta

def chunk_text(text, chunk_size=600):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def load_kb():
    global faiss_index, metadata_store

    print("📚 Loading single KB file:", KB_FILE)

    if not os.path.exists(KB_FILE):
        print("⚠️ KB file not found! RAG will be empty.")
        faiss_index = None
        metadata_store = []
        return

    full_text = read_docx_text(KB_FILE).strip()

    if not full_text:
        print("⚠️ WARNING: Docx file produced EMPTY TEXT!")
        print("👉 Your .docx is not readable as plain text.")
        print("Backend will start but FAISS will be empty.")
        faiss_index = None
        metadata_store = []
        return

    chunks = chunk_text(full_text)

    all_embeddings = []
    metadata_store = []

    for i, chunk in enumerate(chunks):
        embedding = model.encode(chunk)

        meta = extract_metadata_from_chunk(chunk)

        metadata_store.append({
            "source_file": os.path.basename(KB_FILE),
            "kb_id": meta.get("id") or f"chunk-{i}",
            "title": meta.get("title") or "KB Chunk",
            "version": meta.get("version") or "unknown",
            "text": chunk
        })

        all_embeddings.append(embedding)

    embeddings = np.array(all_embeddings).astype("float32")

    dim = embeddings.shape[1]
    faiss_index = faiss.IndexFlatL2(dim)
    faiss_index.add(embeddings)

    print(f"✅ FAISS loaded {len(chunks)} chunks from single KB file.")

def search_kb(query, top_k=3):
    global faiss_index, metadata_store, model

    # Lazy load model and KB
    if faiss_index is None or not metadata_store:
        print("Loading KB for first time...")
        load_kb()

        # If still empty after loading, return empty safely
        if faiss_index is None or not metadata_store:
            print("KB failed to load.")
            return []

    query_emb = model.encode(query).astype("float32").reshape(1, -1)

    distances, indices = faiss_index.search(query_emb, top_k)

    results = []
    for idx in indices[0]:
        results.append(metadata_store[idx])

    return results