import os
import pickle
import faiss
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

# Optional cache path for Render
os.environ["HF_HOME"] = "/tmp/huggingface"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/huggingface"

_model = None
faiss_index = None
metadata_store = None


# -------- LOAD EMBEDDING MODEL (FOR QUERY ONLY) ----------
def get_model():
    global _model
    if _model is None:
        torch.set_grad_enabled(False)
        _model = SentenceTransformer(
            "sentence-transformers/paraphrase-MiniLM-L3-v2",
            device="cpu"
        )
        _model.max_seq_length = 256
        print("✅ Embedding model loaded (query only)")
    return _model


# -------- LOAD PREBUILT FAISS INDEX ----------
def load_kb():
    global faiss_index, metadata_store

    if faiss_index is not None:
        return

    print("📦 Loading prebuilt FAISS index...")

    if not os.path.exists("faiss.index"):
        raise FileNotFoundError("faiss.index not found")

    if not os.path.exists("metadata.pkl"):
        raise FileNotFoundError("metadata.pkl not found")

    faiss_index = faiss.read_index("faiss.index")

    with open("metadata.pkl", "rb") as f:
        metadata_store = pickle.load(f)

    print(f"✅ Loaded {len(metadata_store)} KB chunks")


# -------- SEARCH KB ----------
def search_kb(query, top_k=3):
    global faiss_index, metadata_store

    if faiss_index is None:
        load_kb()

    model = get_model()

    query_emb = model.encode(
        query,
        convert_to_numpy=True
    ).astype("float32").reshape(1, -1)

    distances, indices = faiss_index.search(query_emb, top_k)

    results = []
    for idx in indices[0]:
        if idx < len(metadata_store):
            results.append(metadata_store[idx])

    return results