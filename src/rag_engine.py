"""
RAG Engine Module v3.0 — AI Agent đa luồng: Tự động Web Search khi kho dữ liệu nội bộ trống.

Pipeline cải tiến:
  1. Query Rewriting    — Pháp lý hóa câu hỏi, giữ ngữ cảnh lịch sử an toàn tuyệt đối.
  2. Hybrid Search      — MMR Vector + BM25 + Reciprocal Rank Fusion (Chống ghi đè).
  3. Semantic Grouping  — Gom nhóm theo cây Văn bản → Điều → Khoản.
  4. Structured Prompt  — Đồng bộ UI và tích hợp Guardrail ngắt mạch.
  5. Fallback Web Search— Tự động tìm kiếm Internet (DuckDuckGo) khi không có dữ liệu nội bộ.
"""

import os
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from langchain_core.documents import Document
# pyrefly: ignore [missing-import]
from langchain_chroma import Chroma
# pyrefly: ignore [missing-import]
from langchain_huggingface import HuggingFaceEmbeddings
# pyrefly: ignore [missing-import]
from langchain_google_genai import ChatGoogleGenerativeAI
# pyrefly: ignore [missing-import]
from langchain_core.prompts import ChatPromptTemplate
# pyrefly: ignore [missing-import]
from langchain_community.retrievers import BM25Retriever

# Tải biến môi trường từ file .env
load_dotenv()


class LegalBrainEngine:
    """
    Bộ não xử lý RAG nâng cao v3.0 tối ưu riêng cho hệ thống văn bản Luật Việt Nam.
    Tích hợp Fallback Search Internet.
    """

    def __init__(self, db_path: str = "database"):
        self.db_path = db_path

        print("⏳ Đang khởi tạo Model Embedding (keepitreal/vietnamese-sbert)...")
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="keepitreal/vietnamese-sbert",
            model_kwargs={"device": "cpu"}
        )

        model_name = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
        temperature_val = float(os.getenv("LLM_TEMPERATURE", 0.0))

        print(f"🧠 Đang kết nối Bộ não LLM ({model_name})...")
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature_val,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )

        self.vector_db: Optional[Chroma] = None
        self._docs_cache: List[Document] = []

    # ─────────────────────────────────────────────────────────────
    # QUẢN LÝ VECTOR DATABASE
    # ─────────────────────────────────────────────────────────────

    def create_vector_db(self, all_chunks: List[Dict[str, Any]]):
        if not all_chunks:
            print("❌ Không có chunks dữ liệu nào để tạo Vector DB!")
            return

        print(f"📦 Đang tiến hành Embedding và nạp {len(all_chunks)} chunks vào ChromaDB...")
        self._docs_cache = [
            Document(page_content=chunk["content"], metadata=chunk["metadata"])
            for chunk in all_chunks
        ]
        self.vector_db = Chroma.from_documents(
            documents=self._docs_cache,
            embedding=self.embedding_model,
            persist_directory=self.db_path
        )
        print("✨ Đã khởi tạo và đồng bộ kho Vector Database thành công!")

    def load_existing_db(self) -> bool:
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            self.vector_db = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embedding_model
            )
            self._load_docs_into_cache()
            print("✅ Đã kết nối thành công tới kho dữ liệu Vector DB hiện có.")
            return True
        print("⚠️ Không tìm thấy dữ liệu Vector DB cũ. Cần chạy quá trình khởi tạo mới.")
        return False

    def _load_docs_into_cache(self):
        try:
            result = self.vector_db.get()
            self._docs_cache = [
                Document(page_content=content, metadata=meta)
                for content, meta in zip(result["documents"], result["metadatas"])
            ]
            print(f"📋 Đã cache {len(self._docs_cache)} documents sẵn sàng cho Hybrid Search.")
        except Exception as e:
            print(f"⚠️ Không thể cache documents cho BM25: {e}")
            self._docs_cache = []

    # ─────────────────────────────────────────────────────────────
    # QUERY REWRITING (CÓ HỖ TRỢ BỘ NHỚ LỊCH SỬ)
    # ─────────────────────────────────────────────────────────────

    def _rewrite_query(self, question: str, chat_context: str = "") -> str:
        try:
            # Ép kiểu dữ liệu an toàn tuyệt đối, loại bỏ lỗi cấu trúc List/Dict từ UI đổ về
            if not isinstance(question, str): question = str(question)
            if not isinstance(chat_context, str): chat_context = str(chat_context)

            if chat_context.strip():
                sys_msg = (
                    "Bạn là chuyên gia ngôn ngữ pháp lý Việt Nam. Người dùng vừa lựa chọn một câu hỏi gợi ý nối tiếp "
                    "từ cuộc trò chuyện ngay trước đó.\n\n"
                    "--- BỐI CẢNH TRƯỚC ĐÓ ---\n"
                    "{chat_context}\n"
                    "--------------------------\n\n"
                    "Nhiệm vụ: Hãy phân tích bối cảnh trước đó và viết lại câu hỏi HIỆN TẠI của người dùng thành một câu truy vấn tìm kiếm pháp lý tối ưu, ĐỘC LẬP và ĐẦY ĐỦ Ý NGHĨA. "
                    "Hãy tự động bổ sung chủ ngữ, đối tượng cụ thể hoặc hành vi thực tế từ bối cảnh trước đó vào câu hỏi này. "
                    "CHỈ trả về câu truy vấn đã viết lại, KHÔNG giải thích thêm, KHÔNG tự trả lời câu hỏi."
                )
                rewrite_prompt = ChatPromptTemplate.from_messages([
                    ("system", sys_msg),
                    ("human", "Câu hỏi cần xử lý: {question}"),
                ])
                result = (rewrite_prompt | self.llm).invoke({"question": question, "chat_context": chat_context})
            else:
                sys_msg = (
                    "Bạn là chuyên gia ngôn ngữ và pháp lý Việt Nam. Nhiệm vụ duy nhất của bạn là: "
                    "Chuyển đổi câu hỏi thông thường của người dùng thành một câu truy vấn tìm kiếm pháp lý tối ưu. "
                    "Thêm các thuật ngữ đồng nghĩa hoặc từ khóa chuyên ngành liên quan đến hành vi đó. "
                    "CHỈ trả về câu truy vấn mới, KHÔNG giải thích thêm."
                )
                rewrite_prompt = ChatPromptTemplate.from_messages([
                    ("system", sys_msg),
                    ("human", "Câu hỏi cần xử lý: {question}"),
                ])
                result = (rewrite_prompt | self.llm).invoke({"question": question})
                
            rewritten = result.content.strip()
            print(f"🔄 Query Rewriting:\n   Gốc  : {question}\n   Mới  : {rewritten}")
            return rewritten
        except Exception as e:
            print(f"⚠️ Query Rewriting thất bại ({e}), dùng câu hỏi gốc.")
            return question

    # ─────────────────────────────────────────────────────────────
    # HYBRID SEARCH (MMR + BM25 + RRF)
    # ─────────────────────────────────────────────────────────────

    def _hybrid_search(self, query: str, k: int = 6) -> List[Document]:
        RRF_K = 60 

        vector_retriever = self.vector_db.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k * 2, "fetch_k": 30, "lambda_mult": 0.65}
        )
        vector_docs = vector_retriever.invoke(query)

        bm25_docs: List[Document] = []
        if self._docs_cache:
            bm25_retriever = BM25Retriever.from_documents(self._docs_cache)
            bm25_retriever.k = k * 2
            bm25_docs = bm25_retriever.invoke(query)
        else:
            print("⚠️ BM25 cache rỗng, chỉ dùng Vector Search.")

        scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for rank, doc in enumerate(vector_docs):
            key = doc.page_content
            scores[key] = scores.get(key, 0.0) + 0.6 * (1.0 / (RRF_K + rank + 1))
            doc_map[key] = doc

        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content
            scores[key] = scores.get(key, 0.0) + 0.4 * (1.0 / (RRF_K + rank + 1))
            doc_map[key] = doc

        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [doc_map[key] for key in sorted_keys[:k]]

    # ─────────────────────────────────────────────────────────────
    # SEMANTIC GROUPING
    # ─────────────────────────────────────────────────────────────

    def _semantic_grouping(self, retrieved_docs: List[Document]) -> str:
        grouped: Dict[str, Dict[str, List[str]]] = {}

        for doc in retrieved_docs:
            doc_name = doc.metadata.get("document", "Tài liệu tham khảo")
            article  = doc.metadata.get("article", "Quy định chung")
            khoan    = doc.metadata.get("khoan", "")

            grouped.setdefault(doc_name, {})
            key = f"Điều {article}" + (f" — Khoản {khoan}" if khoan else "")
            grouped[doc_name].setdefault(key, []).append(doc.page_content)

        lines = []
        for doc_name, articles in grouped.items():
            lines.append(f"\n🏢 NGUỒN VĂN BẢN: {doc_name.upper()}")
            for article_key, contents in articles.items():
                lines.append(f"  📌 [{article_key}]")
                for content in contents:
                    lines.append(f"  {content}")

        return "\n".join(lines).strip()

    # ─────────────────────────────────────────────────────────────
    # PIPELINE RAG CHÍNH (VỚI WEB FALLBACK)
    # ─────────────────────────────────────────────────────────────

    def ask_legal_agent(self, question: str, top_k: int = 6, chat_context: str = "") -> Dict[str, Any]:
        if not self.vector_db:
            return {
                "answer": "🔴 Hệ thống chưa được nạp cơ sở dữ liệu luật! Vui lòng tải file PDF lên trước.",
                "sources": [],
                "rewritten_query": question,
            }

        # BƯỚC 1: Query Rewriting
        rewritten_query = self._rewrite_query(question, chat_context)

        # BƯỚC 2: Hybrid Search
        retrieved_docs = self._hybrid_search(rewritten_query, k=top_k)

        if not retrieved_docs:
            return {
                "answer": "🔍 Dựa trên kho dữ liệu hiện tại, tôi không tìm thấy điều luật nào có liên quan đến câu hỏi của bạn.",
                "sources": [],
                "rewritten_query": rewritten_query,
            }

        # BƯỚC 3: Semantic Grouping
        clean_context = self._semantic_grouping(retrieved_docs)

        # BƯỚC 4: Prompt Local RAG
        system_prompt = (
            "Bạn là Trợ lý Chuyên gia Pháp luật cấp cao tại Việt Nam.\n"
            "Giải đáp câu hỏi dựa HOÀN TOÀN vào bối cảnh pháp lý được cung cấp bên dưới.\n\n"

            "⚠️ QUY TẮC BẮT BUỘC:\n"
            "1. CHỈ sử dụng thông tin CÓ TRONG BỐI CẢNH. Tuyệt đối không tự suy diễn hoặc thêm kiến thức bên ngoài.\n"
            "2. NGẮT MẠCH TỰ ĐỘNG: Nếu bối cảnh hoàn toàn KHÔNG liên quan, CHỈ ĐƯỢC PHÉP trả lời đúng 1 câu sau và DỪNG LẠI:\n"
            "'*Kho dữ liệu hiện tại chưa có quy định pháp lý trực tiếp cho tình huống này.*'\n\n"
            "3. CHỈ KHI bối cảnh CÓ ĐỦ THÔNG TIN, bạn mới được phép phân tích và BẮT BUỘC trình bày theo đúng cấu trúc 4 PHẦN sau:\n\n"

            "## 📋 TÓM TẮT\n"
            "- Trả lời trực diện, khẳng định ngay vấn đề trong 2 - 3 câu.\n\n"

            "## 📖 PHÂN TÍCH CHI TIẾT\n"
            "- Phân tích chi tiết, trích dẫn từ khóa/mức phạt (dùng bullet points và bôi đậm).\n\n"

            "## ⚖️ CĂN CỨ PHÁP LÝ\n"
            "- Liệt kê nội dung áp dụng và bắt buộc vẽ Bảng tổng hợp nguồn trích dẫn:\n"
            "| Văn bản/Nguồn | Điều khoản/Chi tiết | Nội dung áp dụng |\n"
            "|---------|-------------|------------------|\n\n"

            "## 💡 CÂU HỎI GỢI Ý\n"
            "- ĐÂY LÀ PHẦN BẮT BUỘC PHẢI CÓ Ở CUỐI CÙNG.\n"
            "- Đề xuất đúng 2 đến 3 câu hỏi tiếp theo để người dùng đào sâu vấn đề.\n"
            "- Bắt đầu mỗi câu bằng dấu gạch ngang (-).\n\n"

            "=== BỐI CẢNH PHÁP LÝ ===\n"
            "{context}\n"
            "========================="
        )

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Câu hỏi cần tư vấn: {question}"),
        ])

        rag_chain = prompt_template | self.llm
        print("🤖 Bộ não AI đang phân tích dữ liệu nội bộ...")
        ai_response = rag_chain.invoke({"context": clean_context, "question": rewritten_query})
        
        final_answer = ai_response.content
        sources = []

        # ── BƯỚC 4.5: AGENT FALLBACK - TỰ ĐỘNG TÌM KIẾM INTERNET NẾU THIẾU DATA ──
        if "*Kho dữ liệu hiện tại chưa có quy định" in final_answer:
            print("🌐 [Web Fallback] Kho nội bộ không có dữ liệu. Đang kích hoạt Agent tìm kiếm Internet...")
            try:
                from langchain_community.tools import DuckDuckGoSearchResults
                from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
                
                # Cấu hình Web Search (Tập trung truy vấn pháp luật Việt Nam)
                wrapper = DuckDuckGoSearchAPIWrapper(region="wt-wt", max_results=4)
                search = DuckDuckGoSearchResults(api_wrapper=wrapper)
                
                # Nâng cấp câu truy vấn để ép công cụ Web tìm Nghị định xử phạt
                web_query = rewritten_query + " quy định pháp luật việt nam nghị định mức phạt"
                web_raw_data = search.run(web_query)
                
                if web_raw_data:
                    # Bơm data từ Web vào Prompt thay thế cho Local PDF
                    web_context = f"TÀI LIỆU TỪ INTERNET:\n{web_raw_data}"
                    print("🤖 Đang tổng hợp lại câu trả lời từ dữ liệu Web...")
                    
                    ai_response_web = rag_chain.invoke({"context": web_context, "question": rewritten_query})
                    final_answer = ai_response_web.content
                    
                    # Bóc tách Link URL từ DuckDuckGo để làm Nguồn trích dẫn
                    links = re.findall(r"link:\s*(https?://[^\],]+)", web_raw_data)
                    sources = [f"🌐 Nguồn Internet: {link}" for link in set(links)]
            except Exception as e:
                print(f"⚠️ Web Search thất bại, hoàn tác về câu trả lời cũ: {e}")

        # ── BƯỚC 5: Source Extraction chuẩn hóa (Nếu lấy từ PDF nội bộ) ──
        if not sources and "*Kho dữ liệu hiện tại chưa có quy định" not in final_answer:
            for doc in retrieved_docs:
                doc_name = doc.metadata.get("document", "")
                article  = doc.metadata.get("article", "")
                khoan    = doc.metadata.get("khoan", "")
                
                if article:
                    label = f"{doc_name} — Điều {article}"
                    if khoan:
                        label += f", Khoản {khoan}"
                else:
                    label = doc.metadata.get("source", doc_name or "Văn bản không tên")
                    
                if label and label not in sources:
                    sources.append(label)

        return {
            "answer": final_answer,
            "sources": sources,
            "rewritten_query": rewritten_query,
        }