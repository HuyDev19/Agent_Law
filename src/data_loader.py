"""
Data Loader Module - Đọc PDF, làm sạch dữ liệu và cắt chunk theo cấu trúc "Điều X." của luật Việt Nam
"""

import os
import re
from pathlib import Path
from typing import List, Dict
from pypdf import PdfReader


class LawDataLoader:
    """
    Xử lý dữ liệu PDF luật pháp Việt Nam
    - Đọc file PDF từ thư mục data/
    - Làm sạch và chuẩn hóa text
    - Cắt chunk theo cấu trúc "Điều X."
    """
    
    def __init__(self, data_path: str = "data"):
        """
        Args:
            data_path: Đường dẫn thư mục chứa file PDF
        """
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
    
    def load_pdfs(self) -> Dict[str, str]:
        """
        Đọc tất cả file PDF từ thư mục data/
        
        Returns:
            Dict[tên_file: nội_dung_text]
        """
        documents = {}
        
        if not self.data_path.exists():
            print(f"⚠️ Thư mục {self.data_path} không tồn tại")
            return documents
        
        pdf_files = list(self.data_path.glob("*.pdf"))
        
        if not pdf_files:
            print(f"⚠️ Không tìm thấy file PDF trong {self.data_path}")
            return documents
        
        for pdf_file in pdf_files:
            try:
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                documents[pdf_file.stem] = text
                print(f"✅ Đã tải: {pdf_file.name}")
            except Exception as e:
                print(f"❌ Lỗi đọc {pdf_file.name}: {e}")
        
        return documents
    
    def clean_text(self, text: str) -> str:
        """
        Làm sạch và chuẩn hóa text
        
        Args:
            text: Text gốc
            
        Returns:
            Text đã làm sạch
        """
        # Xóa khoảng trắng thừa
        text = re.sub(r'\s+', ' ', text)
        # Xóa ký tự đặc biệt không cần thiết
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        return text.strip()
    
    def chunk_by_articles(self, text: str, document_name: str) -> List[Dict[str, str]]:
        """
        Cắt text theo cấu trúc "Điều X." của luật Việt Nam
        
        Args:
            text: Text gốc từ PDF
            document_name: Tên tài liệu (cho metadata)
            
        Returns:
            List các chunk với metadata
        """
        # Pattern: "Điều X." hoặc "Điều X -" (X là số)
        article_pattern = r'(?:Điều|ĐIỀU|Article|ARTICLE)\s+(\d+[a-zA-Z]*)'
        
        # Tìm tất cả vị trí "Điều X"
        matches = list(re.finditer(article_pattern, text, re.IGNORECASE))
        
        if not matches:
            # Nếu không tìm thấy "Điều", trả về toàn bộ text
            return [{
                "content": self.clean_text(text),
                "metadata": {
                    "document": document_name,
                    "article": "None",
                    "source": document_name
                }
            }]
        
        chunks = []
        
        for i, match in enumerate(matches):
            article_num = match.group(1)
            start_pos = match.start()
            
            # End position: bắt đầu của "Điều" tiếp theo hoặc cuối text
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            chunk_text = text[start_pos:end_pos]
            chunk_text = self.clean_text(chunk_text)
            
            if chunk_text:  # Chỉ thêm nếu không rỗng
                chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        "document": document_name,
                        "article": article_num,
                        "source": f"{document_name} - Điều {article_num}"
                    }
                })
        
        print(f"📄 {document_name}: {len(chunks)} Điều được cắt")
        return chunks
    
    def process_all_documents(self) -> List[Dict[str, str]]:
        """
        Xử lý tất cả document: load, làm sạch, cắt chunk
        
        Returns:
            List tất cả chunks từ các document
        """
        all_chunks = []
        
        # Bước 1: Load PDF
        documents = self.load_pdfs()
        
        if not documents:
            print("⚠️ Không có document nào được tải")
            return []
        
        print(f"\n📚 Bắt đầu xử lý {len(documents)} document...\n")
        
        # Bước 2 & 3: Làm sạch và cắt chunk
        for doc_name, text in documents.items():
            cleaned_text = self.clean_text(text)
            chunks = self.chunk_by_articles(cleaned_text, doc_name)
            all_chunks.extend(chunks)
        
        print(f"\n✨ Hoàn tất: {len(all_chunks)} chunks tổng cộng\n")
        return all_chunks
