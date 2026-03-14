import os
import faiss
import numpy as np
from pathlib import Path
from typing import List, Tuple

class FaissStore:
    def __init__(self, index_path: str = None, dimension: int = 384):
        """
        Initializes the FAISS index. Loads from disk if it exists, otherwise creates a new FlatL2 index.
        Default dimension is 384 (all-MiniLM-L6-v2 size).
        """
        if index_path is None:
            root_dir = Path(__file__).resolve().parent.parent
            data_dir = root_dir / "data"
            data_dir.mkdir(exist_ok=True)
            self.index_path = str(data_dir / "vector_index.faiss")
            self.id_map_path = str(data_dir / "vector_ids.npy")
        else:
            self.index_path = index_path
            self.id_map_path = str(Path(index_path).with_suffix(".npy"))

        self.dimension = dimension
        
        # Load or create
        if os.path.exists(self.index_path) and os.path.exists(self.id_map_path):
            print(f"      [Vector Store] Loading local FAISS index from {self.index_path}")
            self.index = faiss.read_index(self.index_path)
            self.doc_ids = list(np.load(self.id_map_path))
        else:
            print(f"      [Vector Store] Initializing new FAISS index")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.doc_ids = []

    def add_embeddings(self, embeddings: np.ndarray, db_ids: List[int]):
        """
        Add batch of embeddings and their corresponding DB Transaction IDs to the index.
        """
        if len(embeddings) == 0:
            return
            
        if len(embeddings) != len(db_ids):
            raise ValueError("Number of embeddings must match number of IDs")
            
        if embeddings.dtype != np.float32:
             embeddings = embeddings.astype(np.float32)

        self.index.add(embeddings)
        self.doc_ids.extend(db_ids)
        self.save()

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[int, float]]:
        """
        Search for top-k similar embeddings.
        Returns a list of tuples: (Transaction ID, Distance)
        """
        if self.index.ntotal == 0:
            return []
            
        # Ensure it's a 2D array [1, dimension] for a single query
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
            
        if query_embedding.dtype != np.float32:
             query_embedding = query_embedding.astype(np.float32)
             
        # FAISS search
        distances, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx != -1 and idx < len(self.doc_ids):
                db_id = self.doc_ids[idx]
                distance = float(distances[0][i])
                results.append((db_id, distance))
                
        return results

    def save(self):
        """Persist index and ID map to disk."""
        faiss.write_index(self.index, self.index_path)
        np.save(self.id_map_path, np.array(self.doc_ids))
