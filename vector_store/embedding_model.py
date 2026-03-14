from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initializes the sentence transformer. 
        Note: The first time this runs, it will download the model weights (~80MB) 
        from HuggingFace. Subsequent runs will use the cached local weights, 
        ensuring 100% offline functionality.
        """
        print(f"      [Vector Store] Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> np.ndarray:
        """Returns the embedding for a single string as a 1D numpy array."""
        if not text:
            return np.zeros(self.dimension, dtype=np.float32)
        # return as float32 for FAISS compatibility
        return self.model.encode(text).astype(np.float32)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Returns stacked embeddings for a list of strings."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        return self.model.encode(texts).astype(np.float32)

embedding_model = EmbeddingModel()
