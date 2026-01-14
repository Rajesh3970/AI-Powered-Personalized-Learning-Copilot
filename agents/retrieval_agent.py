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
        template = """
You are a professional course tutor.

INSTRUCTIONS:
- Use ONLY the provided context
- Do NOT add outside knowledge
- If the answer is missing, clearly say so
- Organize the answer using:
  - Headings
  - Bullet points
  - Numbered steps (if applicable)
- Cite sources inline like: (Source 1), (Source 2)

FORMAT (MANDATORY):
## Short Answer
1–2 sentences summary

## Detailed Explanation
- Bullet points or short paragraphs

## Key Points
- Point 1
- Point 2

## Sources Used
- Source numbers only

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

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
