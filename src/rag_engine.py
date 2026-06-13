"""
RAG Engine Module v2.0 — Kiến trúc RAG nâng cao cho hệ thống tư vấn Luật Việt Nam.

Pipeline cải tiến:
  1. Query Rewriting    — Pháp lý hóa câu hỏi bằng LLM trước khi tìm kiếm
  2. Hybrid Search      — MMR Vector Search + BM25 Keyword Search + Reciprocal Rank Fusion
  3. Semantic Grouping  — Gom nhóm bối cảnh theo cây Văn bản → Điều → Khoản
  4. Structured Prompt  — Ép buộc output 3 phần cố định: Tóm tắt / Phân tích / Căn cứ pháp lý
  5. Source Extraction  — Trích xuất nguồn trích dẫn chuẩn hóa theo metadata
"""

import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.retrievers import BM25Retriever

# Tải biến môi trường từ file .env
load_dotenv()


class LegalBrainEngine:
    """
    Bộ não xử lý RAG nâng cao v2.0 tối ưu riêng cho hệ thống văn bản Luật Việt Nam.
    Pipeline: Query Rewriting → Hybrid Search (MMR + BM25 + RRF) → Semantic Grouping → Structured Output.
    """

    def __init__(self, db_path: str = "database"):
        self.db_path = db_path

        print("⏳ Đang khởi tạo Model Embedding (keepitreal/vietnamese-sbert)...")
        # Sử dụng mô hình SBERT tối ưu riêng cho ngữ nghĩa tiếng Việt
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="keepitreal/vietnamese-sbert",
            model_kwargs={"device": "cpu"}  # Đổi sang 'cuda' nếu máy có GPU Nvidia
        )

        # Đọc cấu hình linh hoạt từ file .env
        model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        temperature_val = float(os.getenv("LLM_TEMPERATURE", 0.0))

        print(f"🧠 Đang kết nối Bộ não LLM ({model_name})...")
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature_val,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )

        self.vector_db: Optional[Chroma] = None
        # Cache toàn bộ documents để cấp cho BM25Retriever
        self._docs_cache: List[Document] = []

    # ─────────────────────────────────────────────────────────────
    # QUẢN LÝ VECTOR DATABASE
    # ─────────────────────────────────────────────────────────────

    def create_vector_db(self, all_chunks: List[Dict[str, Any]]):
        """
        Nhận vào các chunks từ data_loader, tiến hành nhúng vector và lưu vào ChromaDB local.
        """
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
        """
        Tái sử dụng kho dữ liệu Vector đã có sẵn trên ổ đĩa để tiết kiệm tài nguyên.
        """
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            self.vector_db = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embedding_model
            )
            # Nạp toàn bộ documents vào cache cho BM25
            self._load_docs_into_cache()
            print("✅ Đã kết nối thành công tới kho dữ liệu Vector DB hiện có.")
            return True

        print("⚠️ Không tìm thấy dữ liệu Vector DB cũ. Cần chạy quá trình khởi tạo mới.")
        return False

    def _load_docs_into_cache(self):
        """Tải toàn bộ documents từ Chroma vào bộ nhớ để phục vụ BM25Retriever."""
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
    # [NÂNG CẤP 1] QUERY REWRITING
    # ─────────────────────────────────────────────────────────────

    def _rewrite_query(self, question: str) -> str:
        """
        Dùng LLM để viết lại câu hỏi thông thường thành dạng truy vấn pháp lý chính xác,
        bổ sung thuật ngữ chuyên ngành để tối ưu hóa độ chính xác của bước Retrieval.

        Ví dụ:
          Input : "Đi nhậu về lái xe máy bị phạt bao nhiêu?"
          Output: "Mức xử phạt vi phạm hành chính đối với người điều khiển xe mô tô
                   có nồng độ cồn trong máu hoặc hơi thở vượt mức quy định"
        """
        rewrite_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Bạn là chuyên gia pháp lý Việt Nam. Nhiệm vụ DUY NHẤT: "
                "Viết lại câu hỏi bên dưới thành một truy vấn pháp lý súc tích, chính xác, "
                "bổ sung thuật ngữ pháp luật chuyên ngành phù hợp để tối ưu hóa tìm kiếm "
                "trong cơ sở dữ liệu văn bản luật Việt Nam. "
                "Giữ ngắn gọn (tối đa 2 câu). CHỈ trả về câu truy vấn đã viết lại, KHÔNG giải thích.",
            ),
            ("human", "{question}"),
        ])
        try:
            result = (rewrite_prompt | self.llm).invoke({"question": question})
            rewritten = result.content.strip()
            print(f"🔄 Query Rewriting:\n   Gốc  : {question}\n   Mới  : {rewritten}")
            return rewritten
        except Exception as e:
            print(f"⚠️ Query Rewriting thất bại ({e}), dùng câu hỏi gốc.")
            return question

    # ─────────────────────────────────────────────────────────────
    # [NÂNG CẤP 2] HYBRID SEARCH (MMR + BM25 + RRF)
    # ─────────────────────────────────────────────────────────────

    def _hybrid_search(self, query: str, k: int = 6) -> List[Document]:
        """
        [NÂNG CẤP 2] Hybrid Search: Kết hợp MMR Vector Search + BM25 Keyword Search
        qua thuật toán Reciprocal Rank Fusion (RRF) tự implement — không phụ thuộc thư viện ngoài.

        Công thức RRF: score(d) = Σ 1 / (k_rrf + rank_i(d))   với k_rrf = 60
        Vector Search chiếm trọng số 0.6, BM25 chiếm 0.4.
        """
        RRF_K = 60  # Hằng số làm mượt RRF chuẩn

        # ── Vector MMR Search ────────────────────────────────────
        vector_retriever = self.vector_db.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k * 2, "fetch_k": 30, "lambda_mult": 0.65}
        )
        vector_docs = vector_retriever.invoke(query)

        # ── BM25 Keyword Search ──────────────────────────────────
        bm25_docs: List[Document] = []
        if self._docs_cache:
            bm25_retriever = BM25Retriever.from_documents(self._docs_cache)
            bm25_retriever.k = k * 2
            bm25_docs = bm25_retriever.invoke(query)
        else:
            print("⚠️ BM25 cache rỗng, chỉ dùng Vector Search.")

        # ── Reciprocal Rank Fusion ───────────────────────────────
        scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        for rank, doc in enumerate(vector_docs):
            key = doc.page_content[:120]  # Dùng 120 ký tự đầu làm khóa định danh
            scores[key] = scores.get(key, 0.0) + 0.6 * (1.0 / (RRF_K + rank + 1))
            doc_map[key] = doc

        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content[:120]
            scores[key] = scores.get(key, 0.0) + 0.4 * (1.0 / (RRF_K + rank + 1))
            doc_map[key] = doc

        # Sắp xếp theo điểm RRF giảm dần và trả về top-k
        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
        return [doc_map[key] for key in sorted_keys[:k]]

    # ─────────────────────────────────────────────────────────────
    # [NÂNG CẤP 3] SEMANTIC GROUPING CẢI TIẾN
    # ─────────────────────────────────────────────────────────────

    def _semantic_grouping(self, retrieved_docs: List[Document]) -> str:
        """
        Gom nhóm bối cảnh theo cấu trúc cây: Văn bản → Điều → Khoản.
        Giúp LLM đọc context mạch lạc theo trình tự pháp lý, tránh rối loạn logic.
        """
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
    # PIPELINE RAG CHÍNH
    # ─────────────────────────────────────────────────────────────

    def ask_legal_agent(self, question: str, top_k: int = 6) -> Dict[str, Any]:
        """
        Pipeline RAG v2.0 — 5 bước xử lý:
          Bước 1: Query Rewriting    — Pháp lý hóa câu hỏi
          Bước 2: Hybrid Search      — MMR Vector + BM25 + RRF
          Bước 3: Semantic Grouping  — Gom nhóm context có cấu trúc
          Bước 4: Structured Prompt  — Output 3 phần cố định
          Bước 5: Source Extraction  — Trích xuất nguồn trích dẫn chuẩn
        """
        if not self.vector_db:
            return {
                "answer": "🔴 Hệ thống chưa được nạp cơ sở dữ liệu luật! Vui lòng tải file PDF lên trước.",
                "sources": [],
                "rewritten_query": question,
            }

        # ── BƯỚC 1: Query Rewriting ──────────────────────────────
        rewritten_query = self._rewrite_query(question)

        # ── BƯỚC 2: Hybrid Search (MMR + BM25 + RRF) ─────────────
        retrieved_docs = self._hybrid_search(rewritten_query, k=top_k)

        if not retrieved_docs:
            return {
                "answer": (
                    "🔍 Dựa trên kho dữ liệu hiện tại, tôi không tìm thấy điều luật nào "
                    "có liên quan đến câu hỏi của bạn."
                ),
                "sources": [],
                "rewritten_query": rewritten_query,
            }

        # ── BƯỚC 3: Gom nhóm ngữ nghĩa ───────────────────────────
        clean_context = self._semantic_grouping(retrieved_docs)

        # ── BƯỚC 4: Structured System Prompt ─────────────────────
        # [NÂNG CẤP 4] Ép buộc output 3 phần cố định, nhất quán mọi lần trả lời
        system_prompt = (
            "Bạn là Trợ lý Chuyên gia Pháp luật cấp cao tại Việt Nam. "
            "Giải đáp câu hỏi dựa HOÀN TOÀN vào bối cảnh pháp lý được cung cấp bên dưới.\n\n"

            "⚠️ QUY TẮC BẮT BUỘC:\n"
            "1. CHỈ sử dụng thông tin CÓ TRONG BỐI CẢNH. Tuyệt đối không tự suy diễn hoặc thêm kiến thức bên ngoài.\n"
            "2. Nếu bối cảnh không đủ thông tin, ghi rõ: "
            "'*Kho dữ liệu hiện tại chưa có thông tin về vấn đề này.*'\n"
            "3. PHẢI trình bày câu trả lời theo ĐÚNG cấu trúc 3 phần sau (bao gồm tiêu đề):\n\n"

            "---\n"
            "## 📋 TÓM TẮT\n"
            "_[Trả lời trực tiếp câu hỏi trong 1–3 câu ngắn gọn, súc tích]_\n\n"

            "## 📖 PHÂN TÍCH CHI TIẾT\n"
            "_[Phân tích đầy đủ. Dùng bullet points (- hoặc •) cho từng ý. "
            "Bôi đậm **từ khóa / mức phạt / thời hạn** quan trọng. "
            "Dùng bảng Markdown nếu cần so sánh nhiều mức/trường hợp.]_\n\n"

            "## ⚖️ CĂN CỨ PHÁP LÝ\n"
            "| Văn bản | Điều — Khoản | Nội dung áp dụng |\n"
            "|---------|-------------|------------------|\n"
            "_[Điền đầy đủ, mỗi điều luật đã sử dụng là một dòng trong bảng]_\n"
            "---\n\n"

            "=== BỐI CẢNH PHÁP LÝ ===\n"
            "{context}\n"
            "========================="
        )

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Câu hỏi cần tư vấn: {question}"),
        ])

        rag_chain = prompt_template | self.llm
        print("🤖 Bộ não AI đang đối chiếu điều khoản và tổng hợp tư vấn...")
        ai_response = rag_chain.invoke({"context": clean_context, "question": question})

        # ── BƯỚC 5: Source Extraction chuẩn hóa ──────────────────
        # [NÂNG CẤP 5] Định dạng nhất quán "Tên văn bản — Điều X, Khoản Y"
        sources = []
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
            "answer": ai_response.content,
            "sources": sources,
            # Trường bổ sung: UI có thể hiển thị câu hỏi đã được viết lại nếu muốn
            "rewritten_query": rewritten_query,
        }