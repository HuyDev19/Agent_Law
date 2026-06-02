"""
Data Loader Module - Đọc PDF, làm sạch dữ liệu và cắt chunk theo chiến lược:
1. Nhận diện "Điều" -> 2. Nhận diện "Khoản" -> 3. Tiêm Tiêu đề -> 4. Overlap 150 ký tự.
Có bổ sung cơ chế Fallback tự động cắt nếu không nhận diện được cấu trúc Điều.
"""

import os
import re
from pathlib import Path
from typing import List, Dict
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


class LawDataLoader:
    """
    Xử lý dữ liệu PDF luật pháp Việt Nam theo chuẩn RAG nâng cao
    """
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        
        # Khởi tạo công cụ cắt khúc với Overlap (Bước 1 của chiến lược)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, 
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " "]
        )
    
    def load_pdfs(self) -> Dict[str, str]:
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
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                # Kiểm tra nếu file bị rỗng hoàn toàn (Do PDF scan dạng ảnh)
                if not text.strip():
                    print(f"❌ LỖI TRÍCH XUẤT: {pdf_file.name} rỗng chữ (Có thể là PDF ảnh Scan).")
                else:
                    documents[pdf_file.stem] = text
                    print(f"✅ Đã tải: {pdf_file.name}")
            except Exception as e:
                print(f"❌ Lỗi đọc {pdf_file.name}: {e}")
        return documents
    
    def clean_text(self, text: str) -> str:
        # Làm sạch khoảng trắng nhưng giữ cấu trúc dòng
        text = re.sub(r'[ \t]+', ' ', text) 
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        return text.strip()
    
    def chunk_by_articles(self, text: str, document_name: str) -> List[Dict[str, str]]:
        chunks = []
        
        # CẢI TIẾN 1: Regex linh hoạt, không phân biệt hoa thường (?i), chấp nhận chữ Điều bị dính khoảng trắng ẩn
        article_pattern = r'(?i)(?:điều|đ\s*i\s*ề\s*u)\s+(\d+[a-zA-Z]*)'
        matches = list(re.finditer(article_pattern, text))
        
        # CẢI TIẾN 2: Cơ chế lưới đỡ AN TOÀN (Fallback) - Tránh mất file dữ liệu
        if not matches:
            print(f"💡 {document_name}: Không khớp cấu trúc 'Điều' -> Kích hoạt tự động cắt phân đoạn.")
            split_docs = self.text_splitter.split_text(text)
            for idx, split_text in enumerate(split_docs):
                chunk_title = f"📌 Tài liệu: {document_name} (Phần {idx + 1})"
                chunks.append({
                    "content": f"{chunk_title}\n{split_text}",
                    "metadata": {
                        "document": document_name,
                        "article": f"AutoPart_{idx + 1}",
                        "source": f"{document_name} - Phần {idx + 1}"
                    }
                })
            return chunks

        # Xử lý cắt theo Điều/Khoản khi đã tìm thấy các điểm khớp mã luật
        for i, match in enumerate(matches):
            article_num = match.group(1)
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            raw_article_text = text[start_pos:end_pos]
            lines = raw_article_text.split('\n', 1)
            article_title_raw = self.clean_text(lines[0])
            article_body = self.clean_text(lines[1]) if len(lines) > 1 else ""
            
            # Khớp cấu trúc Khoản (Ví dụ: dòng bắt đầu bằng "1.", "2.")
            khoan_pattern = r'(?:\n|^)(\d+\.)\s*(.*?)(?=(?:\n\d+\.|$))'
            khoan_matches = list(re.finditer(khoan_pattern, article_body, re.DOTALL))
            
            if khoan_matches:
                for k_match in khoan_matches:
                    khoan_num = k_match.group(1).strip()
                    khoan_content = k_match.group(2).strip()
                    full_khoan_text = f"{khoan_num} {khoan_content}"
                    
                    split_docs = self.text_splitter.split_text(full_khoan_text)
                    for idx, split_text in enumerate(split_docs):
                        chunk_title = f"📌 Điều {article_num} | Khoản {khoan_num.replace('.', '')}"
                        if len(split_docs) > 1:
                            chunk_title += f" (Phần {idx + 1})"
                            
                        chunks.append({
                            "content": f"{chunk_title}\n{split_text}",
                            "metadata": {
                                "document": document_name,
                                "article": article_num,
                                "khoan": khoan_num.replace('.', ''),
                                "source": f"{document_name} - Điều {article_num} - Khoản {khoan_num.replace('.', '')}"
                            }
                        })
            else:
                split_docs = self.text_splitter.split_text(article_body)
                for idx, split_text in enumerate(split_docs):
                    chunk_title = f"📌 Điều {article_num}"
                    if len(split_docs) > 1:
                        chunk_title += f" (Phần {idx + 1})"
                        
                    chunks.append({
                        "content": f"{chunk_title}\n{article_title_raw}\n{split_text}",
                        "metadata": {
                            "document": document_name,
                            "article": article_num,
                            "source": f"{document_name} - Điều {article_num}"
                        }
                    })
                    
        print(f"📄 {document_name}: Tạo thành công {len(chunks)} chunks tối ưu")
        return chunks

    def process_all_documents(self) -> List[Dict[str, str]]:
        all_chunks = []
        documents = self.load_pdfs()
        
        if not documents:
            return []
            
        print(f"\n📚 Bắt đầu xử lý {len(documents)} document...\n")
        for doc_name, text in documents.items():
            chunks = self.chunk_by_articles(text, doc_name)
            all_chunks.extend(chunks)
            
        print(f"\n✨ Hoàn tất: {len(all_chunks)} chunks tổng cộng\n")
        return all_chunks