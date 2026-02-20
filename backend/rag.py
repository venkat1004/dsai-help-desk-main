import os
import re
import numpy as np
import faiss
import docx
import torch
from sentence_transformers import SentenceTransformer

# -------- SET HUGGINGFACE CACHE TO SAFE LOCATION --------
os.environ["HF_HOME"] = "/tmp/huggingface"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/huggingface"

# -------- YOUR SINGLE KB FILE --------
KB_FILE = r"C:\Users\venkatsai.reddy\Downloads\KB File List.docx"
# -------------------------------------

# -------- GLOBALS --------
_model = None
faiss_index = None
metadata_store = []

# -------- LOAD LIGHTWEIGHT MODEL LAZILY --------
def get_model():
    global _model
    if _model is None:
        torch.set_grad_enabled(False)
        _model = SentenceTransformer(
            "sentence-transformers/paraphrase-MiniLM-L3-v2",
            device="cpu"
        )
        _model.max_seq_length = 256
        print("✅ Lightweight embedding model loaded")
    return _model

# -------- READ DOCX SAFELY ----------
def read_docx_text(path):
    doc = docx.Document(path)
    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return text

# -------- EXTRACT METADATA ----------
def extract_metadata_from_chunk(chunk):
    meta = {"id": None, "title": None, "version": None}

    id_match = re.search(r"id:\s*(.+)", chunk, re.IGNORECASE)
    title_match = re.search(r"title:\s*(.+)", chunk, re.IGNORECASE)
    version_match = re.search(r"version:\s*(.+)", chunk, re.IGNORECASE)

    if id_match:
        meta["id"] = id_match.group(1).strip()
    if title_match:
        meta["title"] = title_match.group(1).strip()
    if version_match:
        meta["version"] = version_match.group(1).strip()

    return meta

# -------- CHUNK TEXT ----------
def chunk_text(text, chunk_size=600):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# -------- LOAD KB ----------
def load_kb():
    global faiss_index, metadata_store

    print("📚 Loading single KB file:", KB_FILE)

    if not os.path.exists(KB_FILE):
        print("⚠️ KB file not found")
        faiss_index = None
        metadata_store = []
        return

    full_text = read_docx_text(KB_FILE).strip()

    if not full_text:
        print("⚠️ Empty KB file")
        faiss_index = None
        metadata_store = []
        return

    chunks = chunk_text(full_text)

    model = get_model()

    all_embeddings = []
    metadata_store = []

    for i, chunk in enumerate(chunks):

        embedding = model.encode(
            chunk,
            batch_size=1,
            convert_to_numpy=True,
            show_progress_bar=False
        )

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

    print(f"✅ FAISS loaded {len(chunks)} chunks")

# -------- SEARCH KB ----------
def search_kb(query, top_k=3):
    global faiss_index, metadata_store

    if faiss_index is None or not metadata_store:
        print("Loading KB for first time...")
        load_kb()

        if faiss_index is None:
            return []

    model = get_model()

    query_emb = model.encode(
        query,
        batch_size=1,
        convert_to_numpy=True,
        show_progress_bar=False
    ).astype("float32").reshape(1, -1)

    distances, indices = faiss_index.search(query_emb, top_k)

    results = []
    for idx in indices[0]:
        if idx < len(metadata_store):
            results.append(metadata_store[idx])

    return results