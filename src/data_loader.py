"""
Data Loader Module - Đọc PDF, làm sạch dữ liệu và cắt chunk theo chiến lược:
1. Nhận diện "Điều" -> 2. Nhận diện "Khoản" -> 3. Tiêm Ngữ cảnh Văn bản -> 4. Overlap 150 ký tự.
Có bổ sung cơ chế Fallback tự động cắt nếu không nhận diện được cấu trúc Điều.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
# pyrefly: ignore [missing-import]
from pypdf import PdfReader
# pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json


class LawDataLoader:
    """
    Xử lý dữ liệu PDF luật pháp Việt Nam theo chuẩn RAG nâng cao
    """
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        self.tracking_file = self.data_path / "processed_files.json"
        
        # Khởi tạo công cụ cắt khúc với Overlap (Bước 1 của chiến lược)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, 
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " "]
        )
    
    def get_processed_files(self) -> List[str]:
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def mark_as_processed(self, filenames: List[str]):
        if not filenames:
            return
        processed = self.get_processed_files()
        processed.extend([f for f in filenames if f not in processed])
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False, indent=4)
    
    def load_pdfs(self) -> Tuple[Dict[str, str], List[str]]:
        documents = {}
        new_files = []
        if not self.data_path.exists():
            print(f"⚠️ Thư mục {self.data_path} không tồn tại")
            return documents, new_files
        
        processed_files = self.get_processed_files()
        pdf_files = [f for f in self.data_path.glob("*.pdf") if f.name not in processed_files]
        
        if not pdf_files:
            print("💡 Không có file PDF nào mới cần xử lý.")
            return documents, new_files
        
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
                    new_files.append(pdf_file.name)
                    print(f"✅ Đã tải file mới: {pdf_file.name}")
            except Exception as e:
                print(f"❌ Lỗi đọc {pdf_file.name}: {e}")
        return documents, new_files
    
    def clean_text(self, text: str) -> str:
        # Làm sạch khoảng trắng nhưng giữ cấu trúc dòng
        text = re.sub(r'[ \t]+', ' ', text) 
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        return text.strip()
    
    def chunk_by_articles(self, text: str, document_name: str) -> List[Dict[str, str]]:
        chunks = []
        
        # Regex linh hoạt, không phân biệt hoa thường (?i), chấp nhận chữ Điều bị dính khoảng trắng ẩn
        article_pattern = r'(?i)(?:điều|đ\s*i\s*ề\s*u)\s+(\d+[a-zA-Z]*)'
        matches = list(re.finditer(article_pattern, text))
        
        # Cơ chế lưới đỡ AN TOÀN (Fallback) - Tránh mất file dữ liệu nếu cấu trúc văn bản dị biệt
        if not matches:
            print(f"💡 {document_name}: Không khớp cấu trúc 'Điều' -> Kích hoạt tự động cắt phân đoạn.")
            split_docs = self.text_splitter.split_text(text)
            for idx, split_text in enumerate(split_docs):
                chunk_title = f"🏢 Văn bản: {document_name} | 📌 Phần {idx + 1}"
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
                        # NÂNG CẤP: Tiêm rõ tên Văn bản vào tiêu đề chunk nội dung để tối ưu hóa mô hình Embedding
                        clean_khoan_num = khoan_num.replace('.', '')
                        chunk_title = f"🏢 Văn bản: {document_name} | 📌 Điều {article_num} | Khoản {clean_khoan_num}"
                        if len(split_docs) > 1:
                            chunk_title += f" (Phần {idx + 1})"
                            
                        chunks.append({
                            "content": f"{chunk_title}\n{split_text}",
                            "metadata": {
                                "document": document_name,
                                "article": article_num,
                                "khoan": clean_khoan_num,
                                "source": f"{document_name} — Điều {article_num}, Khoản {clean_khoan_num}"
                            }
                        })
            else:
                split_docs = self.text_splitter.split_text(article_body)
                for idx, split_text in enumerate(split_docs):
                    chunk_title = f"🏢 Văn bản: {document_name} | 📌 Điều {article_num}"
                    if len(split_docs) > 1:
                        chunk_title += f" (Phần {idx + 1})"
                        
                    chunks.append({
                        "content": f"{chunk_title}\n{article_title_raw}\n{split_text}",
                        "metadata": {
                            "document": document_name,
                            "article": article_num,
                            "source": f"{document_name} — Điều {article_num}"
                        }
                    })
                    
        print(f"📄 {document_name}: Tạo thành công {len(chunks)} chunks tối ưu cấu trúc pháp lý.")
        return chunks

    def process_all_documents(self) -> Tuple[List[Dict[str, str]], List[str]]:
        all_chunks = []
        documents, new_files = self.load_pdfs()
        
        if not documents:
            return [], []
            
        print(f"\n📚 Bắt đầu xử lý {len(documents)} document mới...\n")
        for doc_name, text in documents.items():
            chunks = self.chunk_by_articles(text, doc_name)
            all_chunks.extend(chunks)
            
        print(f"\n✨ Hoàn tất: {len(all_chunks)} chunks tổng cộng cho các file mới\n")
        return all_chunks, new_files