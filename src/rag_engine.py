"""
RAG Engine Module - Tạo mã Embedding, lưu trữ vào Vector DB (Chroma) 
và thực hiện truy vấn kết hợp Gom nhóm Ngữ nghĩa (Semantic Grouping) với Gemini.
"""

import os
from typing import List, Dict
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Tải biến môi trường từ file .env (Để lấy GEMINI_API_KEY)
load_dotenv()

class LegalBrainEngine:
    """
    Bộ não xử lý RAG nâng cao cho Luật Việt Nam
    """
    
    def __init__(self, db_path: str = "database"):
        self.db_path = db_path
        
        print("⏳ Đang khởi tạo Model Embedding (keepitreal/vietnamese-sbert)...")
        # Sử dụng model SBERT chuyên dụng cho tiếng Việt như cấu hình đề ra
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="keepitreal/vietnamese-sbert",
            model_kwargs={'device': 'cpu'} # Chuyển thành 'cuda' nếu máy có GPU Nvidia
        )
        
        print("🧠 Đang kết nối Bộ não LLM (Gemini Pro)...")
        # Cấu hình Gemini với temperature = 0 để AI tuyệt đối không tự chế luật
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        self.vector_db = None

    def create_vector_db(self, all_chunks: List[Dict[str, str]]):
        """
        Nhận vào list các chunks từ data_loader, tiến hành nhúng vector và lưu vào ổ đĩa local
        """
        if not all_chunks:
            print("❌ Không có chunks dữ liệu nào để tạo Vector DB!")
            return
            
        print(f"📦 Đang tiến hành Embedding và lưu {len(all_chunks)} chunks vào ChromaDB tại '{self.db_path}'...")
        
        # Chuyển đổi định dạng từ Dict của data_loader sang Object Document của Langchain
        langchain_docs = []
        for chunk in all_chunks:
            doc = Document(
                page_content=chunk["content"],
                metadata=chunk["metadata"]
            )
            langchain_docs.append(doc)
            
        # Tạo và lưu trữ Vector DB
        self.vector_db = Chroma.from_documents(
            documents=langchain_docs,
            embedding=self.embedding_model,
            persist_directory=self.db_path
        )
        print("✨ Đã khởi tạo và lưu trữ kho Vector Database thành công!")

    def load_existing_db(self):
        """
        Load lại kho dữ liệu Vector đã có sẵn trên ổ đĩa (Không cần chạy lại khâu embedding tốn thời gian)
        """
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            self.vector_db = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embedding_model
            )
            print("✅ Đã kết nối thành công tới kho dữ liệu Vector DB hiện có.")
            return True
        else:
            print("⚠️ Không tìm thấy dữ liệu Vector DB cũ. Cần chạy quá trình khởi tạo mới.")
            return False

    def _semantic_grouping(self, retrieved_docs: List[Document]) -> str:
        """
        [BƯỚC 4 VÀ 5 TRONG CHIẾN LƯỢC]
        Gom nhóm các đoạn văn bản truy xuất được theo từng FILE và từng ĐIỀU LUẬT 
        để tạo mạch ngữ cảnh liên tục, giúp LLM đọc hiểu logic nhất.
        """
        grouped_data = {}
        
        for doc in retrieved_docs:
            doc_name = doc.metadata.get("document", "Khác")
            article = doc.metadata.get("article", "Chung")
            
            if doc_name not in grouped_data:
                grouped_data[doc_name] = {}
            if article not in grouped_data[doc_name]:
                grouped_data[doc_name][article] = []
                
            grouped_data[doc_name][article].append(doc.page_content)
            
        # Nối dữ liệu lại thành một chuỗi văn bản mạch lạc
        context_string = ""
        for doc_name, articles in grouped_data.items():
            context_string += f"\n=== NGUỒN TÀI LIỆU: {doc_name} ===\n"
            for article_num, contents in articles.items():
                context_string += f"\n[Các khoản thuộc Điều/Phần {article_num}]:\n"
                for content in contents:
                    # Loại bỏ phần tiêu đề lặp lại nếu có để text gọn sạch hơn
                    context_string += f"{content}\n"
                    
        return context_string.strip()

    def ask_legal_agent(self, question: str) -> Dict[str, any]:
        """
        Xử lý quy trình RAG: Nhận câu hỏi -> Tìm kiếm -> Gom nhóm -> Gọi Gemini -> Trả kết quả
        """
        if not self.vector_db:
            return {"answer": "Hệ thống chưa nạp cơ sở dữ liệu luật!", "sources": []}
            
        # 1. Truy xuất top 5 đoạn văn bản liên quan nhất từ Vector DB
        retrieved_docs = self.vector_db.similarity_search(question, k=5)
        
        # 2. Thực hiện chiến thuật Semantic Grouping (Sắp xếp lại bối cảnh)
        clean_context = self._semantic_grouping(retrieved_docs)
        
        # 3. Xây dựng Prompt nghiêm ngặt cho LLM (Chống ảo giác cấu trúc luật)
        system_prompt = (
            "Bạn là một chuyên gia lập pháp tối cao tại Việt Nam. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng "
            "một cách chính xác, khách quan dựa trên bối cảnh pháp lý được cung cấp dưới đây.\n\n"
            "⚠️ QUY TẮC BẮT BUỘC:\n"
            "1. Chỉ trả lời dựa VÀO THÔNG TIN CÓ TRONG BỐI CẢNH. Không tự bịa đặt, không suy diễn thiếu căn cứ.\n"
            "2. Nếu thông tin trong bối cảnh không đủ để trả lời, hãy nói thẳng: 'Dựa trên kho dữ liệu luật hiện tại, tôi không tìm thấy thông tin này.'\n"
            "3. Cuối câu trả lời, hãy liệt kê rõ ràng các Điều luật và Tên văn bản mà bạn đã dùng làm căn cứ (Trích xuất từ bối cảnh).\n\n"
            "=== BỐI CẢNH PHÁP LÝ ===\n"
            "{context}\n"
            "========================"
        )
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Câu hỏi: {question}")
        ])
        
        # 4. Kích hoạt chuỗi và gọi Gemini Pro
        rag_chain = prompt_template | self.llm
        print("🤖 Gemini đang đọc luật và tổng hợp câu trả lời...")
        ai_response = rag_chain.invoke({"context": clean_context, "question": question})
        
        # 5. Thu thập nguồn trích dẫn (Metadata) để hiển thị lên UI sau này
        sources = []
        for doc in retrieved_docs:
            source_info = doc.metadata.get("source", "Không rõ nguồn")
            if source_info not in sources:
                sources.append(source_info)
                
        return {
            "answer": ai_response.content,
            "sources": sources
        }