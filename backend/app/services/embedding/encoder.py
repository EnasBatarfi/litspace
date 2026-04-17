# This module provides functionality for encoding text into embeddings using a pre-trained SentenceTransformer model. It includes device detection to utilize GPU if available and caching of the model for efficient reuse.

from __future__ import annotations

from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

from app.core.config import settings


def detect_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    device = detect_device()
    model = SentenceTransformer(settings.embedding_model, device=device)
    return model


def embed_texts(texts: list[str], batch_size: int = 16):
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings