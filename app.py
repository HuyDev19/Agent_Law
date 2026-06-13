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
    if "current_query" not in st.session_state:
        st.session_state.current_query = ""
    if "current_result" not in st.session_state:
        st.session_state.current_result = None
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
                st.warning(
                    "⚠️ Không thể nạp dữ liệu. Lý do có thể là:\n"
                    "- Thư mục `data/` không có file PDF nào.\n"
                    "- Các file PDF là ảnh scan, không có nội dung text.\n"
                    "- File PDF bị lỗi hoặc trống."
                )
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
        
        # Tải lên và xử lý PDF
        st.subheader("Tải lên & Xử lý PDF")
        uploaded_files = st.file_uploader(
            "Chọn hoặc kéo thả file PDF vào đây:",
            type="pdf",
            accept_multiple_files=True,
            help="Bạn có thể tải lên nhiều file. Các file này sẽ được thêm vào thư mục 'data'."
        )

        if st.button("🔄 Xử lý & Nạp Dữ liệu", use_container_width=True, type="primary"):
            if uploaded_files:
                data_path = Path("data")
                data_path.mkdir(exist_ok=True)
                
                saved_files_count = 0
                overwritten_files = []
                new_files = []

                for uploaded_file in uploaded_files:
                    file_path = data_path / uploaded_file.name
                    if file_path.exists():
                        overwritten_files.append(uploaded_file.name)
                    else:
                        new_files.append(uploaded_file.name)

                    try:
                        # Save file to data directory
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        saved_files_count += 1
                    except Exception as e:
                        st.error(f"Lỗi khi lưu file {uploaded_file.name}: {e}")
                
                if saved_files_count > 0:
                    st.toast(f"Đã lưu thành công {saved_files_count} file PDF.")
                    if new_files:
                        st.info(f"📁 File mới được thêm: {', '.join(new_files)}")
                    if overwritten_files:
                        st.warning(f"⚠️ File đã được ghi đè: {', '.join(overwritten_files)}")

            # Luôn chạy load và index, nó sẽ quét toàn bộ thư mục 'data'
            load_and_index_data()
            st.rerun()
        
        # Settings (Lưu ý: Mặc định trong code src đang lấy k=5 cố định tại hàm ask_legal_agent, slider này tạm phục vụ hiển thị cấu trúc UI)
        st.subheader("🔧 Tham Số RAG")
        st.session_state.top_k = st.slider("Số lượng Điều luật bối cảnh (Top-K):", 1, 10, st.session_state.top_k)
        
        st.divider()
        
        # Lịch sử queries
        st.subheader("📋 Lịch Sử Tra Cứu")
        if st.session_state.query_history:
            # Hiển thị 5 câu hỏi gần nhất, mới nhất ở trên
            for history_item in reversed(st.session_state.query_history[-5:]):
                query_text = history_item['query']
                # Dùng st.button để có thể click vào, key để tránh lỗi trùng lặp
                if st.button(f"📜 {query_text[:45]}...", key=f"history_{query_text}", help=query_text, use_container_width=True):
                    # Khi click, gán câu hỏi này vào ô nhập liệu chính và hiển thị lại kết quả cũ
                    st.session_state.current_query = query_text
                    st.session_state.current_result = history_item
                    st.rerun()
        else:
            st.caption("Lịch sử tra cứu sẽ hiện ở đây.")
    
    # Main content
    if not st.session_state.data_loaded:
        st.info("""
        ### 📚 Hướng dẫn khởi động hệ thống:
        
        1. **Tải lên file luật (PDF)** bằng công cụ ở thanh menu bên trái.
        2. Nhấp nút **"Xử lý & Nạp Dữ liệu"** để AI tiến hành đọc và ghi nhớ nội dung.
        3. Sau khi có thông báo thành công, ô **Nhập câu hỏi** sẽ xuất hiện.
        
        *Lưu ý: Hệ thống cũng sẽ tự động nhận diện các file PDF bạn đã đặt sẵn trong thư mục `data`.*
        """)
    else:
        # Query interface
        st.header("🔍 Cửa sổ Tra cứu Pháp lý")
        
        # Ô nhập liệu được kiểm soát bởi session_state để nhận giá trị từ lịch sử
        query = st.text_input(
            "Nhập tình huống hoặc câu hỏi pháp lý của bạn:",
            placeholder="VD: Quyền lao động của người lao động là gì?",
            value=st.session_state.get("current_query", "")
        )
        # Cập nhật lại state nếu người dùng gõ tay vào ô nhập liệu
        st.session_state.current_query = query
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            search_button = st.button("🔎 Trích xuất câu trả lời", use_container_width=True, type="primary")
        
        with col2:
            clear_button = st.button("🔄 Làm mới", use_container_width=True)
        
        if clear_button:
            st.session_state.current_query = ""
            st.session_state.current_result = None
            st.rerun()
        
        # Xử lý truy vấn câu hỏi bằng bộ não LegalBrainEngine
        if search_button and query.strip():
            with st.spinner("🤖 Trợ lý đang lục tìm các văn bản luật và tổng hợp câu trả lời..."):
                try:
                    # SỬA LỖI GỌI HÀM: Chuyển từ .query() sang .ask_legal_agent() trả về Dict
                    result = st.session_state.rag_engine.ask_legal_agent(query)
                    
                    # Tạo mục mới cho lịch sử và kết quả hiện tại
                    new_history_item = {
                        "query": query,
                        "answer": result.get("answer", "Không có câu trả lời."),
                        "sources": result.get("sources", [])
                    }
                    st.session_state.current_result = new_history_item

                    # Cập nhật lịch sử tra cứu: Xóa nếu đã tồn tại và thêm lại vào cuối để thành mới nhất
                    st.session_state.query_history = [h for h in st.session_state.query_history if h['query'] != query]
                    st.session_state.query_history.append(new_history_item)
                    
                except Exception as e:
                    st.error(f"❌ Xảy ra lỗi trong quá trình sinh văn bản: {str(e)}")
                    st.session_state.current_result = None # Xóa kết quả nếu có lỗi
        elif search_button:
            st.warning("⚠️ Vui lòng nhập nội dung câu hỏi.")

        # Hiển thị kết quả hiện tại (từ tra cứu mới hoặc từ lịch sử)
        if st.session_state.current_result:
            result = st.session_state.current_result
            response = result.get("answer", "Không có câu trả lời.")
            sources = result.get("sources", [])
            
            st.markdown("### 📝 Kết quả tư vấn:")
            st.info(response)
            
            if sources:
                st.markdown("#### 📂 Văn bản căn cứ trích xuất:")
                for source in sources:
                    st.caption(f"• {source}")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #999; font-size: 0.9em;">
        <p>🤖 Hệ Thống RAG Tra Cứu Luật Pháp Việt Nam | Sử dụng ChromaDB & Gemini 2.5 Pro</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()