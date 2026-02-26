import os
import pickle
import numpy as np
import faiss
import docx
import re
from sentence_transformers import SentenceTransformer

KB_FILE = "KB File List.docx"

def read_docx_text(path):
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

def extract_metadata_from_chunk(chunk):
    meta = {"id": None}
    match = re.search(r"id:\s*(.+)", chunk, re.IGNORECASE)
    if match:
        meta["id"] = match.group(1).strip()
    return meta

def chunk_text(text, chunk_size=600):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

print("Loading model...")
model = SentenceTransformer("sentence-transformers/paraphrase-MiniLM-L3-v2")

print("Reading KB...")
text = read_docx_text(KB_FILE)
chunks = chunk_text(text)

embeddings = []
metadata = []

for i, chunk in enumerate(chunks):
    emb = model.encode(chunk, convert_to_numpy=True)
    embeddings.append(emb)

    meta = extract_metadata_from_chunk(chunk)
    metadata.append({
        "kb_id": meta.get("id") or f"chunk-{i}",
        "text": chunk
    })

embeddings = np.array(embeddings).astype("float32")

print("Creating FAISS index...")
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, "faiss.index")

with open("metadata.pkl", "wb") as f:
    pickle.dump(metadata, f)

print("Done. Index saved.")