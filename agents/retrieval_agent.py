from services.llm_client import llm_client
from services.vector_store import vector_store
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from typing import Dict, List

class RetrievalAgent:
    """Retrieval Agent - Performs semantic search and generates citation-aware responses"""
    
    def __init__(self):
        self.llm = llm_client
        self.vector_store = vector_store
    
    def answer_question(self, course_name: str, question: str) -> Dict:
        """RAG-based question answering with citations"""
        
        # Step 1: Semantic search over course content
        retrieved_chunks = self.vector_store.semantic_search(
            course_name=course_name,
            query=question,
            n_results=5
        )
        
        if not retrieved_chunks:
            return {
                "answer": "I don't have enough course materials to answer this question. Please upload PDFs first.",
                "sources": [],
                "relevant_chunks": 0
            }
        
        # Step 2: Build context from retrieved chunks
        context_parts = []
        sources = set()
        
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_parts.append(f"[Source {i}: {chunk['source']}]\n{chunk['text']}")
            sources.add(chunk['source'])
        
        context = "\n\n".join(context_parts)
        
        # Step 3: Generate citation-aware response
        template = """You are a helpful course tutor. Answer the student's question using ONLY the provided course materials.

IMPORTANT RULES:
1. Base your answer ONLY on the context provided
2. Cite sources explicitly (e.g., "According to [Source 1]...")
3. If the answer isn't in the context, say so clearly
4. Be concise but thorough
5. Use simple, clear language

Context from course materials:
{context}

Student Question: {question}

Answer:"""

        variables = {
            "context": context,
            "question": question
        }
        
        answer = self.llm.generate_with_template(template, variables)
        
        return {
            "answer": answer.strip(),
            "sources": list(sources),
            "relevant_chunks": len(retrieved_chunks)
        }

retrieval_agent = RetrievalAgent()