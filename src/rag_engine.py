"""
RAG Engine Module - Kết nối Vector Database, Embeddings và LLM (Gemini)
"""

import os
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import chromadb
from chromadb.config import Settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class RAGEngine:
    """
    RAG Engine - Quản lý Vector Database, Embeddings và LLM
    - Lưu trữ chunks vào ChromaDB
    - Tìm kiếm semantic tương ứng queries
    - Sử dụng Gemini Pro để sinh response
    """
    
    def __init__(self, db_path: str = "database", model_name: str = "keepitreal/vietnamese-sbert"):
        """
        Khởi tạo RAG Engine
        
        Args:
            db_path: Đường dẫn thư mục lưu ChromaDB
            model_name: Tên embedding model HuggingFace
        """
        load_dotenv()
        
        self.db_path = db_path
        self.model_name = model_name
        
        # Khởi tạo ChromaDB
        self.chroma_client = chromadb.HttpClient(
            host="localhost",
            port=8000
        ) if os.getenv("CHROMADB_MODE") == "server" else self._init_local_chroma()
        
        # Khởi tạo Embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # Khởi tạo LLM (Gemini Pro)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        self.collection = None
    
    def _init_local_chroma(self):
        """Khởi tạo ChromaDB local"""
        os.makedirs(self.db_path, exist_ok=True)
        return chromadb.Client(
            Settings(
                chroma_db_impl="duckdb",
                persist_directory=self.db_path,
                anonymized_telemetry=False
            )
        )
    
    def add_documents(self, chunks: List[Dict[str, str]], collection_name: str = "law_database"):
        """
        Thêm chunks vào Vector Database
        
        Args:
            chunks: List các chunk với content và metadata
            collection_name: Tên collection trong ChromaDB
        """
        if not chunks:
            print("⚠️ Không có chunks để thêm")
            return
        
        # Tạo hoặc lấy collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Thêm documents
        ids = []
        documents = []
        metadatas = []
        
        for idx, chunk in enumerate(chunks):
            chunk_id = f"doc_{idx}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            metadatas.append(chunk.get("metadata", {}))
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"✅ Đã thêm {len(chunks)} chunks vào ChromaDB")
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, Dict, float]]:
        """
        Tìm kiếm semantic trong Vector Database
        
        Args:
            query: Câu hỏi/query từ user
            top_k: Số kết quả trả về
            
        Returns:
            List (content, metadata, similarity_score)
        """
        if not self.collection:
            print("⚠️ Collection chưa được khởi tạo")
            return []
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        search_results = []
        
        if results["documents"] and results["documents"][0]:
            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            ):
                # Chuyển distance thành similarity (cosine: 0=giống nhất, 1=khác nhất)
                similarity = 1 - distance
                search_results.append((doc, metadata, similarity))
        
        return search_results
    
    def generate_response(
        self,
        query: str,
        context_docs: List[Tuple[str, Dict, float]]
    ) -> str:
        """
        Sinh response từ Gemini dựa trên context
        
        Args:
            query: Câu hỏi của user
            context_docs: List context từ search()
            
        Returns:
            Response từ Gemini
        """
        if not context_docs:
            return "❌ Xin lỗi, không tìm thấy thông tin liên quan trong cơ sở dữ liệu luật pháp."
        
        # Xây dựng context prompt
        context_text = ""
        sources = set()
        
        for idx, (content, metadata, score) in enumerate(context_docs, 1):
            context_text += f"\n[Nguồn {idx}] {metadata.get('source', 'Unknown')}:\n{content}\n"
            sources.add(metadata.get('source', 'Unknown'))
        
        # Tạo prompt cho Gemini
        system_prompt = """Bạn là một chuyên gia pháp luật Việt Nam. 
Trả lời câu hỏi của user dựa CHÍNH XÁC trên thông tin được cung cấp dưới đây.
Nếu thông tin không có trong context, hãy nói rõ ràng "Không tìm thấy thông tin" thay vì suy luận.
Luôn trích dẫn nguồn (Điều, Bộ luật) khi đưa ra thông tin.
Sử dụng tiếng Việt, trả lời ngắn gọn và rõ ràng."""
        
        user_prompt = f"""CONTEXT:
{context_text}

CÂUHỎI: {query}

Hãy trả lời dựa trên context trên."""
        
        # Gọi Gemini
        try:
            response = self.llm.invoke(user_prompt)
            answer = response.content
            
            # Thêm trích dẫn nguồn
            sources_text = "\n\n📚 **Nguồn tham khảo:**\n" + "\n".join([f"- {s}" for s in sources])
            return answer + sources_text
            
        except Exception as e:
            return f"❌ Lỗi khi gọi Gemini: {str(e)}"
    
    def query(self, query: str, top_k: int = 3) -> str:
        """
        Wrapper: Tìm kiếm + Sinh response
        
        Args:
            query: Câu hỏi của user
            top_k: Số context trả về
            
        Returns:
            Response cuối cùng
        """
        # Tìm kiếm context
        context_docs = self.search(query, top_k=top_k)
        
        # Sinh response
        response = self.generate_response(query, context_docs)
        
        return response
