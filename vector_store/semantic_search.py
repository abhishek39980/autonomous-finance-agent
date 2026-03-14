from typing import List, Dict, Any

from .embedding_model import embedding_model
from .faiss_index import FaissStore
from database.db_manager import db
from database.models import Transaction

# Singleton instance
faiss_store = FaissStore()

class SemanticSearch:
    @staticmethod
    def embed_and_store_transactions(transactions: List[Transaction]):
        """
        Convert a list of Transactions into embeddings and store them in FAISS.
        """
        if not transactions:
            return

        texts_to_embed = []
        db_ids = []
        
        for tx in transactions:
            # Create a rich text representation for better semantic matching
            cat = str(tx.category) if tx.category else "Unknown"
            merch = str(tx.merchant) if tx.merchant else "Unknown"
            desc = str(tx.raw_description) if tx.raw_description else ""
            amt_str = f"spent {abs(tx.amount)}" if tx.amount < 0 else f"received {abs(tx.amount)}"
            
            # e.g., "Category: Food. Merchant: Zomato. Amount: spent 450. Description: UPI/ZOMATO/food order"
            text_rep = f"Category: {cat}. Merchant: {merch}. Amount: {amt_str}. Description: {desc}"
            
            texts_to_embed.append(text_rep)
            db_ids.append(tx.id)

        # Batch embed
        embeddings = embedding_model.embed_batch(texts_to_embed)
        
        # Store
        faiss_store.add_embeddings(embeddings, db_ids)

    @staticmethod
    def search_transactions(query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Given a natural language query, return the top-k matching transactions from DB.
        """
        if not query:
            return []
            
        # 1. Embed query
        query_emb = embedding_model.embed_text(query)
        
        # 2. Search FAISS
        faiss_results = faiss_store.search(query_emb, k=k)
        if not faiss_results:
             return []
             
        # Extract the database IDs
        target_ids = [result[0] for result in faiss_results]
        
        # 3. Retrieve from SQLite
        session = db.get_session()
        try:
             # Fast query using IN clause
             txs = session.query(Transaction).filter(Transaction.id.in_(target_ids)).all()
             
             # Convert to dict and maintain order of relevance from FAISS
             tx_dict = {tx.id: tx.to_dict() for tx in txs}
             ordered_results = [tx_dict[tid] for tid in target_ids if tid in tx_dict]
             return ordered_results
        finally:
             session.close()

semantic_search = SemanticSearch()
