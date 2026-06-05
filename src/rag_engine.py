"""
RAG Engine Module - Tạo mã Embedding, lưu trữ vào Vector DB (Chroma) 
và thực hiện truy vấn nâng cao kết hợp Gom nhóm Ngữ nghĩa (Semantic Grouping) với Gemini 2.5.
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Tải biến môi trường từ file .env
load_dotenv()

class LegalBrainEngine:
    """
    Bộ não xử lý RAG nâng cao tối ưu riêng cho hệ thống văn bản Luật Việt Nam
    """
    
    def __init__(self, db_path: str = "database"):
        self.db_path = db_path
        
        print("⏳ Đang khởi tạo Model Embedding (keepitreal/vietnamese-sbert)...")
        # Sử dụng mô hình SBERT tối ưu riêng cho ngữ nghĩa tiếng Việt
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="keepitreal/vietnamese-sbert",
            model_kwargs={'device': 'cpu'}  # Đổi sang 'cuda' nếu máy chạy có GPU Nvidia
        )
        
        # Đọc cấu hình linh hoạt từ file .env (Bảo mật và dễ nâng cấp mô hình)
        model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        temperature_val = float(os.getenv("LLM_TEMPERATURE", 0.0))
        
        print(f"🧠 Đang kết nối Bộ não LLM ({model_name})...")
        self.llm = ChatGoogleGenerativeAI(
            model=model_name, 
            temperature=temperature_val,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        self.vector_db = None

    def create_vector_db(self, all_chunks: List[Dict[str, Any]]):
        """
        Nhận vào các chunks từ data_loader, tiến hành nhúng vector và lưu vào ChromaDB local
        """
        if not all_chunks:
            print("❌ Không có chunks dữ liệu nào để tạo Vector DB!")
            return
            
        print(f"📦 Đang tiến hành Embedding và nạp {len(all_chunks)} chunks vào ChromaDB...")
        
        langchain_docs = []
        for chunk in all_chunks:
            doc = Document(
                page_content=chunk["content"],
                metadata=chunk["metadata"]
            )
            langchain_docs.append(doc)
            
        self.vector_db = Chroma.from_documents(
            documents=langchain_docs,
            embedding=self.embedding_model,
            persist_directory=self.db_path
        )
        print("✨ Đã khởi tạo và đồng bộ kho Vector Database thành công!")

    def load_existing_db(self) -> bool:
        """
        Tái sử dụng kho dữ liệu Vector đã có sẵn trên ổ đĩa để tiết kiệm tài nguyên
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
        Chiến thuật Gom nhóm Ngữ nghĩa: Sắp xếp lại bối cảnh theo cấu trúc cây (Tài liệu -> Điều luật)
        giúp LLM không bị rối loạn logic khi đọc các phân đoạn bị cắt tỉa.
        """
        grouped_data = {}
        
        for doc in retrieved_docs:
            doc_name = doc.metadata.get("document", "Tài liệu tham khảo")
            article = doc.metadata.get("article", "Quy định chung")
            
            if doc_name not in grouped_data:
                grouped_data[doc_name] = {}
            if article not in grouped_data[doc_name]:
                grouped_data[doc_name][article] = []
                
            grouped_data[doc_name][article].append(doc.page_content)
            
        context_string = ""
        for doc_name, articles in grouped_data.items():
            context_string += f"\n🏢 NGUỒN VĂN BẢN: {doc_name.upper()}\n"
            for article_num, contents in articles.items():
                context_string += f"📌 [Căn cứ pháp lý: {article_num}]\n"
                for content in contents:
                    context_string += f"- {content}\n"
                    
        return context_string.strip()

    def ask_legal_agent(self, question: str) -> Dict[str, Any]:
        """
        Quy trình RAG tối ưu hóa: Truy xuất đa dạng dạng thức (MMR) -> Gom nhóm -> Chống ảo giác bằng Prompt -> Phản hồi
        """
        if not self.vector_db:
            return {"answer": "🔴 Hệ thống chưa được nạp cơ sở dữ liệu luật! Vui lòng tải file PDF lên trước.", "sources": []}
            
        # 1. Sử dụng kỹ thuật MMR để tìm kiếm đa dạng bối cảnh văn bản, tránh lấy trùng lặp thông tin lân cận
        # fetch_k=20: Quét nhanh 20 đoạn gần nhất; k=6: Chắt lọc ra 6 đoạn có tính bao quát phân tán tốt nhất
        retriever = self.vector_db.as_retriever(
            search_type="mmr",
            search_kwargs={'k': 6, 'fetch_k': 20, 'lambda_mult': 0.65}
        )
        retrieved_docs = retriever.invoke(question)
        
        # Nếu không tìm thấy bất kỳ đoạn bối cảnh nào phù hợp
        if not retrieved_docs:
            return {"answer": "🔍 Dựa trên kho dữ liệu hiện tại, tôi không tìm thấy điều luật nào có liên quan đến câu hỏi của bạn.", "sources": []}
        
        # 2. Gom nhóm ngữ nghĩa để tạo mạch văn bản liên tục cho bộ não AI
        clean_context = self._semantic_grouping(retrieved_docs)
        
        # 3. System Prompt chuyên gia cấp cao (Bảo vệ tính pháp lý, chống AI tự biên tự diễn)
        system_prompt = (
            "Bạn là một Trợ lý Chuyên gia Pháp luật tối cao tại Việt Nam. Nhiệm vụ của bạn là giải đáp thắc mắc "
            "của người dùng một cách cực kỳ chính xác, khách quan và chuyên nghiệp dựa trên bối cảnh pháp lý được cung cấp.\n\n"
            "⚠️ QUY TẮC PHÁP LÝ TỐI CAO:\n"
            "1. Chỉ sử dụng thông tin CÓ TRONG BỐI CẢNH PHÁP LÝ để lập luận. Không tự suy diễn chủ quan, không thêm thắt các kiến thức bên ngoài bối cảnh.\n"
            "2. Nếu bối cảnh không có thông tin hoặc không đủ dữ liệu làm rõ, bắt buộc phải trả lời: 'Dựa trên kho dữ liệu luật hiện tại, tôi không tìm thấy thông tin này để tư vấn cho bạn.' Không được cố gắng tự sáng tác điều luật.\n"
            "3. Hãy trình bày câu trả lời rõ ràng bằng Markdown: sử dụng đầu mục (Bullet points), bôi đậm các từ khóa quan trọng hoặc bảng so sánh nếu cần thiết.\n"
            "4. Cuối câu trả lời, hãy tạo một mục riêng mang tên '⚖️ CĂN CỨ PHÁP LÝ TRÍCH DẪN:' để liệt kê rõ ràng tên các Điều luật, Văn bản pháp luật đã dùng (Trích xuất từ metadata hoặc nội dung bối cảnh).\n\n"
            "=== BỐI CẢNH PHÁP LÝ CUNG CẤP ===\n"
            "{context}\n"
            "================================="
        )
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Câu hỏi cần tư vấn: {question}")
        ])
        
        # 4. Thực hiện lệnh gọi chuỗi xử lý thông qua Gemini
        rag_chain = prompt_template | self.llm
        print("🤖 Bộ não AI đang đối chiếu điều khoản và tổng hợp tư vấn...")
        ai_response = rag_chain.invoke({"context": clean_context, "question": question})
        
        # 5. Thu thập nguồn trích dẫn sạch (Metadata) trả về cho giao diện UI Streamlit hiển thị
        sources = []
        for doc in retrieved_docs:
            # Ưu tiên lấy trường 'document' hoặc 'source' tùy thuộc vào cấu trúc của data_loader của bạn
            source_info = doc.metadata.get("document") or doc.metadata.get("source") or "Văn bản không tên"
            if source_info not in sources:
                sources.append(source_info)
                
        return {
            "answer": ai_response.content,
            "sources": sources
        }