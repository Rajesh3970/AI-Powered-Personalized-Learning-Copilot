import pymupdf as fitz
from typing import List, Dict
import os

class PDFProcessor:
    """Extract and chunk PDF content for embedding"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from PDF"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                text += f"\n\n--- Page {page_num + 1} ---\n\n{page_text}"
            doc.close()
            return text
        except Exception as e:
            print(f"❌ PDF extraction error: {e}")
            return ""
    
    def chunk_text(self, text: str, source_file: str) -> List[Dict[str, str]]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < text_length:
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size // 2:
                    chunk_text = text[start:start + break_point + 1]
                    end = start + break_point + 1
            
            chunks.append({
                "text": chunk_text.strip(),
                "source": source_file,
                "chunk_id": len(chunks)
            })
            
            start = end - self.overlap
        
        return chunks
    
    def process_pdf(self, pdf_path: str, filename: str) -> List[Dict]:
        """Extract and chunk a PDF file"""
        print(f"📄 Processing PDF: {filename}")
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text:
            return []
        
        chunks = self.chunk_text(text, filename)
        print(f"✅ Created {len(chunks)} chunks from {filename}")
        
        return chunks

pdf_processor = PDFProcessor()