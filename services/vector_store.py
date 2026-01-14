import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import os
import re

class ChromaVectorStore:
    """ChromaDB vector store for semantic search (as per documentation)"""
    
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = os.getenv("CHROMA_DIR", "./data/chroma_db")
        
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize embedding model (Sentence Transformers)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        print(f"✅ ChromaDB initialized at {persist_directory}")
        print(f"✅ Embedding model: all-MiniLM-L6-v2 loaded")
    
    def get_or_create_collection(self, course_name: str):
        """Get or create a collection for a course"""
        
        # Sanitize collection name to meet ChromaDB requirements:
        # - Only alphanumeric, underscores, and hyphens
        # - 3-63 characters
        # - Start and end with alphanumeric
        
        # Convert to lowercase
        collection_name = course_name.lower()
        
        # Remove all special characters except alphanumeric, spaces, hyphens, underscores
        collection_name = re.sub(r'[^a-z0-9\s\-_]', '', collection_name)
        
        # Replace spaces and multiple underscores/hyphens with single underscore
        collection_name = re.sub(r'[\s_-]+', '_', collection_name)
        
        # Remove leading/trailing underscores or hyphens
        collection_name = collection_name.strip('_-')
        
        # Ensure it's between 3-63 characters
        if len(collection_name) < 3:
            collection_name = collection_name + "_col"
        if len(collection_name) > 63:
            collection_name = collection_name[:63].rstrip('_-')
        
        # Ensure it starts and ends with alphanumeric
        if not collection_name[0].isalnum():
            collection_name = 'c' + collection_name[1:]
        if not collection_name[-1].isalnum():
            collection_name = collection_name[:-1] + 'c'
        
        print(f"📦 ChromaDB collection name: '{collection_name}' (from '{course_name}')")
        
        collection = self.client.get_or_create_collection(name=collection_name)
        return collection
    
    def add_documents(self, course_name: str, chunks: List[Dict]):
        """Add document chunks to ChromaDB"""
        if not chunks:
            print("⚠️  No chunks to add")
            return
        
        collection = self.get_or_create_collection(course_name)
        
        # Extract texts and generate embeddings
        texts = [chunk['text'] for chunk in chunks]
        print(f"🔄 Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True).tolist()
        
        # Prepare metadata and IDs
        ids = [f"{course_name}_{chunk['source']}_{chunk['chunk_id']}" for chunk in chunks]
        # Sanitize IDs too (remove special characters)
        ids = [re.sub(r'[^a-zA-Z0-9_-]', '_', id_str) for id_str in ids]
        
        metadatas = [{'source': chunk['source'], 'chunk_id': chunk['chunk_id']} for chunk in chunks]
        
        # Add to collection
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Added {len(chunks)} chunks to ChromaDB for course: {course_name}")
    
    def semantic_search(self, course_name: str, query: str, n_results: int = 5) -> List[Dict]:
        """Perform semantic search over course content"""
        collection = self.get_or_create_collection(course_name)
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Search
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        # Format results
        retrieved_chunks = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                retrieved_chunks.append({
                    'text': doc,
                    'source': results['metadatas'][0][i].get('source', 'unknown'),
                    'distance': results['distances'][0][i] if 'distances' in results else 0.0
                })
        
        return retrieved_chunks

vector_store = ChromaVectorStore()
