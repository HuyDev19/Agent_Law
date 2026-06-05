"""
Streamlit App - Giao diện chính của hệ thống Agent AI tra cứu luật pháp Việt Nam
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# Load biến môi trường
load_dotenv()

# SỬA LỖI ĐƯỜNG DẪN IMPORT: Gọi chính xác class LegalBrainEngine từ src.rag_engine
from src.data_loader import LawDataLoader
from src.rag_engine import LegalBrainEngine

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
        font-weight: bold;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1em;
        margin-bottom: 2em;
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
    if "top_k" not in st.session_state:
        st.session_state.top_k = 3


def load_and_index_data():
    """Tải dữ liệu từ PDF và indexing vào Vector DB"""
    with st.spinner("⏳ Đang xử lý và nhúng dữ liệu vào não AI..."):
        try:
            # Bước 1: Load và cắt chunk từ data_loader
            loader = LawDataLoader(data_path="data")
            chunks = loader.process_all_documents()
            
            if not chunks:
                st.warning("⚠️ Không tìm thấy file PDF trong thư mục data/")
                return False
            
            # Bước 2: Khởi tạo LegalBrainEngine và nạp dữ liệu (create_vector_db)
            rag_engine = LegalBrainEngine(db_path="database")
            rag_engine.create_vector_db(chunks)
            
            st.session_state.rag_engine = rag_engine
            st.session_state.data_loaded = True
            
            st.success(f"✅ Đã tải và indexing {len(chunks)} phân đoạn luật thành công!")
            return True
            
        except Exception as e:
            st.error(f"❌ Lỗi xử lý dữ liệu: {str(e)}")
            return False


def main():
    """Hàm main của Streamlit App"""
    
    # Khởi tạo state
    init_session_state()
    
    # Tự động kết nối lại DB cũ nếu đã có thư mục database từ trước để user đỡ phải bấm nút nạp lại
    if st.session_state.rag_engine is None:
        if os.path.exists("database") and os.listdir("database"):
            try:
                rag_engine = LegalBrainEngine(db_path="database")
                if rag_engine.load_existing_db():
                    st.session_state.rag_engine = rag_engine
                    st.session_state.data_loaded = True
            except Exception:
                pass
    
    # Header
    st.markdown('<div class="main-title">⚖️ Trợ Lý AI Tra Cứu Luật Việt Nam</div>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Hệ thống xử lý ngôn ngữ tự nhiên ứng dụng RAG & Gemini Pro</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Bảng Điều Khiển")
        
        # Kiểm tra API Key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("❌ Chưa cấu hình GEMINI_API_KEY trong file .env")
            st.info("Vui lòng tạo file .env và thêm: GEMINI_API_KEY=your_key_here")
            st.stop()
        else:
            st.success("✅ Đã kết nối API Gemini")
        
        st.divider()
        
        # Nút load dữ liệu
        if st.button("🔄 Nạp Dữ Liệu PDF Mới", use_container_width=True, type="primary"):
            load_and_index_data()
        
        # Trạng thái dữ liệu
        if st.session_state.data_loaded:
            st.success("✅ Dữ liệu luật đã sẵn sàng")
        else:
            st.info("📄 Nhấp nút trên để hệ thống quét các file PDF trong thư mục data/")
        
        st.divider()
        
        # Settings (Lưu ý: Mặc định trong code src đang lấy k=5 cố định tại hàm ask_legal_agent, slider này tạm phục vụ hiển thị cấu trúc UI)
        st.subheader("🔧 Tham Số RAG")
        st.session_state.top_k = st.slider("Số lượng Điều luật bối cảnh (Top-K):", 1, 10, st.session_state.top_k)
        
        st.divider()
        
        # Lịch sử queries
        if st.session_state.query_history:
            st.subheader("📋 Lịch Sử Tra Cứu")
            for i, q in enumerate(st.session_state.query_history[-5:], 1):
                st.text(f"{i}. {q[:40]}...")
    
    # Main content
    if not st.session_state.data_loaded:
        st.info("""
        ### 📚 Hướng dẫn khởi động hệ thống:
        
        1. **Đặt file luật (PDF)** vào thư mục `data/` của dự án.
        2. Nhấp nút **"Nạp Dữ Liệu PDF Mới"** ở thanh menu bên trái để AI tiến hành đọc và nhúng vector.
        3. Sau khi có thông báo thành công, ô **Nhập câu hỏi** sẽ xuất hiện.
        """)
        
        # Auto-load nếu có data sẵn (Tránh bắt user bấm nút nhiều lần)
        if os.path.exists("data") and list(Path("data").glob("*.pdf")):
            if st.button("🚀 Khởi Động Nhanh (Sử dụng dữ liệu có sẵn)"):
                load_and_index_data()
                st.rerun()
    else:
        # Query interface
        st.header("🔍 Cửa sổ Tra cứu Pháp lý")
        
        query = st.text_input(
            "Nhập tình huống hoặc câu hỏi pháp lý của bạn:",
            placeholder="VD: Quyền lao động của người lao động là gì?"
        )
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_button = st.button("🔎 Trích xuất câu trả lời", use_container_width=True, type="primary")
        
        with col2:
            clear_button = st.button("🔄 Làm mới", use_container_width=True)
        
        if clear_button:
            st.rerun()
        
        # Xử lý truy vấn câu hỏi bằng bộ não LegalBrainEngine
        if search_button and query.strip():
            st.session_state.query_history.append(query)
            
            with st.spinner("🤖 Trợ lý đang lục tìm các văn bản luật và tổng hợp câu trả lời..."):
                try:
                    # SỬA LỖI GỌI HÀM: Chuyển từ .query() sang .ask_legal_agent() trả về Dict
                    result = st.session_state.rag_engine.ask_legal_agent(query)
                    
                    response = result.get("answer", "Không có câu trả lời.")
                    sources = result.get("sources", [])
                    
                    # Hiển thị Kết quả tư vấn
                    st.markdown("### 📝 Kết quả tư vấn:")
                    st.info(response)
                    
                    # Hiển thị Nguồn trích dẫn văn bản luật nếu có
                    if sources:
                        st.markdown("#### 📂 Văn bản căn cứ trích xuất:")
                        for source in sources:
                            st.caption(f"• {source}")
                    
                except Exception as e:
                    st.error(f"❌ Xảy ra lỗi trong quá trình sinh văn bản: {str(e)}")
        elif search_button:
            st.warning("⚠️ Vui lòng nhập nội dung câu hỏi.")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #999; font-size: 0.9em;">
        <p>🤖 Hệ Thống RAG Tra Cứu Luật Pháp Việt Nam | Sử dụng ChromaDB & Gemini 2.5 Pro</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()