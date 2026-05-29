"""
Streamlit App - Giao diện chính của hệ thống Agent AI tra cứu luật pháp Việt Nam
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

import streamlit as st
from data_loader import LawDataLoader
from rag_engine import RAGEngine


# Cấu hình Streamlit
st.set_page_config(
    page_title="Agent Tra Cứu Luật Pháp Việt Nam",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1E40AF;
        font-size: 2.5em;
        margin-bottom: 0.5em;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1em;
        margin-bottom: 2em;
    }
    .response-box {
        background-color: #F0F9FF;
        padding: 1em;
        border-radius: 0.5em;
        border-left: 4px solid #1E40AF;
        margin-top: 1em;
    }
    .sources-box {
        background-color: #F0FDF4;
        padding: 1em;
        border-radius: 0.5em;
        border-left: 4px solid #16A34A;
        margin-top: 1em;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Khởi tạo session state"""
    if "rag_engine" not in st.session_state:
        st.session_state.rag_engine = None
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "query_history" not in st.session_state:
        st.session_state.query_history = []


def load_and_index_data():
    """Tải dữ liệu từ PDF và indexing vào Vector DB"""
    with st.spinner("⏳ Đang xử lý dữ liệu..."):
        try:
            # Bước 1: Load và cắt chunk
            loader = LawDataLoader(data_path="data")
            chunks = loader.process_all_documents()
            
            if not chunks:
                st.warning("⚠️ Không tìm thấy file PDF trong thư mục data/")
                return False
            
            # Bước 2: Khởi tạo RAG Engine
            rag_engine = RAGEngine(db_path="database")
            rag_engine.add_documents(chunks)
            
            st.session_state.rag_engine = rag_engine
            st.session_state.data_loaded = True
            
            st.success(f"✅ Đã tải và indexing {len(chunks)} chunks thành công!")
            return True
            
        except Exception as e:
            st.error(f"❌ Lỗi: {str(e)}")
            return False


def main():
    """Hàm main của Streamlit App"""
    
    # Khởi tạo
    init_session_state()
    
    # Header
    st.markdown('<h1 class="main-title">⚖️ Agent Tra Cứu Luật Pháp Việt Nam</h1>', 
                unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Hệ thống AI hỗ trợ tra cứu luật pháp sử dụng RAG và Gemini</p>', 
                unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Cài Đặt")
        
        # Kiểm tra API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("❌ Chưa cấu hình GEMINI_API_KEY trong .env")
            st.info("Vui lòng tạo file .env và thêm: GEMINI_API_KEY=your_key")
            st.stop()
        else:
            st.success("✅ GEMINI_API_KEY đã được cấu hình")
        
        st.divider()
        
        # Nút load dữ liệu
        if st.button("🔄 Tải Dữ Liệu Mới", use_container_width=True, type="primary"):
            load_and_index_data()
        
        # Trạng thái
        if st.session_state.data_loaded:
            st.success("✅ Dữ liệu đã sẵn sàng")
        else:
            st.info("📄 Nhấp nút trên để tải dữ liệu từ thư mục data/")
        
        st.divider()
        
        # Settings
        st.subheader("🔧 Tham Số")
        top_k = st.slider("Số document trả về (top-k):", 1, 10, 3)
        
        st.divider()
        
        # Lịch sử queries
        if st.session_state.query_history:
            st.subheader("📋 Lịch Sử Câu Hỏi")
            for i, q in enumerate(st.session_state.query_history[-5:], 1):
                st.text(f"{i}. {q[:50]}...")
    
    # Main content
    if not st.session_state.data_loaded:
        st.info("""
        ### 📚 Cách Sử Dụng:
        
        1. **Đặt file PDF** vào thư mục `data/`
        2. **Nhấp nút "Tải Dữ Liệu Mới"** ở sidebar để indexing
        3. **Nhập câu hỏi** dưới đây
        
        ### 📋 Yêu Cầu:
        - File PDF chứa luật Việt Nam
        - Cấu trúc với "Điều X." (sẽ được tự động cắt chunk)
        - GEMINI_API_KEY được cấu hình trong .env
        
        ### 🎯 Ví Dụ Câu Hỏi:
        - Quyền lao động của người lao động là gì?
        - Thế nào là hợp đồng lao động không xác định thời hạn?
        - Điều 36 Bộ luật Lao động nói gì?
        """)
        
        # Auto-load nếu có data sẵn
        if os.path.exists("data") and list(Path("data").glob("*.pdf")):
            if st.button("🚀 Tự Động Tải Dữ Liệu Có Sẵn"):
                load_and_index_data()
    else:
        # Query interface
        st.header("🔍 Tra Cứu")
        
        query = st.text_area(
            "Nhập câu hỏi của bạn:",
            placeholder="VD: Quyền lao động của người lao động là gì?",
            height=80
        )
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_button = st.button("🔎 Tra Cứu", use_container_width=True, type="primary")
        
        with col2:
            clear_button = st.button("🔄 Xóa", use_container_width=True)
        
        if clear_button:
            st.rerun()
        
        # Xử lý query
        if search_button and query.strip():
            st.session_state.query_history.append(query)
            
            with st.spinner("⏳ Đang xử lý..."):
                try:
                    response = st.session_state.rag_engine.query(query, top_k=top_k)
                    
                    # Hiển thị response
                    st.markdown(f'<div class="response-box">{response}</div>', 
                              unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Lỗi: {str(e)}")
        elif search_button:
            st.warning("⚠️ Vui lòng nhập câu hỏi")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #999; font-size: 0.9em;">
        <p>🤖 Agent Tra Cứu Luật Pháp | Sử dụng RAG + Gemini | v0.1.0</p>
        <p><small>Dữ liệu lưu trữ trong ChromaDB | Embeddings: Vietnamese SBERT</small></p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
