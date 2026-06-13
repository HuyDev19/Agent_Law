"""
Streamlit App v2.0 - Giao diện Chatbot cho Agent AI tra cứu luật pháp Việt Nam
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
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

# CSS tùy chỉnh cho giao diện SaaS hiện đại
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* General Styling */
    body {
        font-family: 'Inter', sans-serif;
        color: #CBD5E1; /* Slate 300 - Default text color */
    }

    /* Hide Streamlit's default elements */
    footer {
        visibility: hidden;
        height: 0;
        position: absolute;
    }
    #MainMenu { visibility: hidden; }

    /* Style header to be visible for hamburger menu, but blend in */
    [data-testid="stHeader"] {
        background-color: #0F172A; /* Slate 900 */
    }

    /* Main App Container */
    [data-testid="stAppViewContainer"] {
        background-color: #0F172A; /* Slate 900 */
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #1E293B; /* Slate 800 */
        border-right: 1px solid #334155; /* Slate 700 */
        padding: 1.5rem 1rem;
    }

    /* Sidebar Title/Logo */
    .sidebar-logo {
        font-size: 1.75em;
        font-weight: 700;
        color: #F1F5F9; /* Slate 100 */
        padding-bottom: 1rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid #334155; /* Slate 700 */
    }

    /* Sidebar Buttons (History & New Chat) */
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent;
        color: #94A3B8; /* Slate 400 */
        border: none;
        text-align: left;
        font-weight: 500;
        padding: 0.75rem 0.5rem;
        border-radius: 0.5rem;
        width: 100%;
        transition: background-color 0.2s, color 0.2s;
        display: flex;
        align-items: center;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #334155; /* Slate 700 */
        color: #F1F5F9; /* Slate 100 */
    }
    
    /* Primary CTA Button in Sidebar */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background-color: #4F46E5; /* Indigo 600 */
        color: white;
        font-weight: 600;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background-color: #4338CA; /* Indigo 700 */
    }

    /* File Uploader Styling */
    [data-testid="stFileUploader"] {
        border: 1px solid #334155; /* Slate 700 */
        background-color: #1E293B; /* Slate 800 */
        border-radius: 0.5rem;
    }
    [data-testid="stFileUploader"] label {
        font-weight: 500;
        color: #CBD5E1; /* Slate 300 */
    }

    /* Main Content Area */
    .main-header {
        font-size: 2.25em;
        font-weight: 700;
        color: #F8FAFC; /* Slate 50 */
        text-align: center;
        padding: 1rem 0 2rem 0;
    }

    /* Chat Interface */
    [data-testid="stChatInput"] {
        background-color: #0F172A; /* Slate 900 */
    }
    
    /* AI Response Card */
    .response-card {
        background-color: #1E293B; /* Slate 800 */
        border: 1px solid #334155; /* Slate 700 */
        border-radius: 0.75rem;
        padding: 1.5rem;
        margin-top: 1rem;
        box-shadow: none; /* Shadows are less effective on dark themes */
    }

    .summary-section {
        background-color: #334155; /* Slate 700 */
        border: 1px solid #475569; /* Slate 600 */
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }

    .response-card h2 {
        font-size: 1.1em;
        font-weight: 600;
        color: #F1F5F9; /* Slate 100 */
        border-bottom: 1px solid #334155; /* Slate 700 */
        padding-bottom: 0.5rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    
    .response-card h2:first-child {
        margin-top: 0;
    }

    /* Streamlit specific overrides for dark theme */
    [data-testid="stCaption"] {
        color: #94A3B8; /* Slate 400 */
    }
    .st-emotion-cache-nahz7x a { /* Links in markdown */
        color: #818CF8; /* Indigo 400 */
    }
    /* Success/Info/Warning/Error boxes text color */
    [data-testid="stAlert"] * {
        color: #0F172A !important; /* Dark text for light-colored boxes */
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Khởi tạo session state cho giao diện chat"""
    if "rag_engine" not in st.session_state:
        st.session_state.rag_engine = None
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state: # Lưu trữ các cặp Q&A trong quá khứ
        st.session_state.history = []
    if "top_k" not in st.session_state:
        st.session_state.top_k = 5 # Mặc định là 5 theo yêu cầu mới


def load_and_index_data():
    """Tải dữ liệu từ PDF và indexing vào Vector DB"""
    with st.spinner("⏳ Đang kiểm tra và nhúng dữ liệu mới vào não AI..."):
        try:
            # Bước 1: Load và cắt chunk từ data_loader
            loader = LawDataLoader(data_path="data")
            chunks, new_files = loader.process_all_documents()
            
            # Bước 2: Khởi tạo LegalBrainEngine nếu chưa có hoặc load DB cũ
            if st.session_state.rag_engine is None:
                rag_engine = LegalBrainEngine(db_path="database")
                if os.path.exists("database") and os.listdir("database"):
                    rag_engine.load_existing_db()
                st.session_state.rag_engine = rag_engine
                st.session_state.data_loaded = True
            
            if not chunks:
                if st.session_state.data_loaded:
                    st.info("✅ Dữ liệu hiện tại đã được đồng bộ, không có file PDF nào mới cần xử lý.")
                else:
                    st.warning("⚠️ Không tìm thấy file PDF nào trong thư mục `data/` để nạp.")
                return True
            
            # Nạp dữ liệu mới vào DB
            st.session_state.rag_engine.create_vector_db(chunks)
            
            # Đánh dấu các file mới đã nạp thành công để lần sau bỏ qua
            loader.mark_as_processed(new_files)
            
            st.session_state.data_loaded = True
            st.success(f"✅ Đã tải và indexing {len(chunks)} phân đoạn luật mới thành công!")
            return True
            
        except Exception as e:
            st.error(f"❌ Lỗi xử lý dữ liệu: {str(e)}")
            return False


def render_assistant_response(result: dict):
    """Hiển thị câu trả lời có cấu trúc của AI trong một thẻ được định dạng."""
    answer = result.get("answer", "Không có câu trả lời.")
    sources = result.get("sources", [])

    with st.container():
        st.markdown('<div class="response-card">', unsafe_allow_html=True)
        
        # Tách câu trả lời thành các phần dựa trên tiêu đề Markdown
        # LLM được yêu cầu tạo ra các tiêu đề: ## TÓM TẮT, ## PHÂN TÍCH CHI TIẾT, ## CĂN CỨ PHÁP LÝ
        parts = re.split(r'##\s*(?:📋\s*TÓM TẮT|📖\s*PHÂN TÍCH CHI TIẾT|⚖️\s*CĂN CỨ PHÁP LÝ)', answer)
        parts = [p.strip() for p in parts if p.strip()]

        # Bọc phần tóm tắt trong một div riêng có style
        if len(parts) > 0:
            st.markdown('<h2>📋 TÓM TẮT</h2>', unsafe_allow_html=True)
            # Sử dụng st.markdown để hiển thị nội dung tóm tắt bên trong div
            summary_html = f'<div class="summary-section">{parts[0]}</div>'
            st.markdown(summary_html, unsafe_allow_html=True)
        
        # Hiển thị các phần còn lại
        if len(parts) > 1:
            st.markdown('<h2>📖 PHÂN TÍCH CHI TIẾT</h2>', unsafe_allow_html=True)
            st.markdown(parts[1], unsafe_allow_html=True)
        if len(parts) > 2:
            st.markdown('<h2>⚖️ CĂN CỨ PHÁP LÝ</h2>', unsafe_allow_html=True)
            st.markdown(parts[2], unsafe_allow_html=True)

        # Hiển thị các nguồn tài liệu đã trích xuất
        if sources:
            st.markdown('<div class="source-citation" style="padding-top: 1.5rem; font-size: 0.9em;">', unsafe_allow_html=True)
            st.markdown('<p style="font-weight: 600; color: #E2E8F0;">📂 Văn bản căn cứ trích xuất:</p>', unsafe_allow_html=True)
            for source in sources:
                st.caption(f"• {source}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)


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
    # Sidebar
    with st.sidebar:
        st.markdown('<div class="sidebar-logo">⚖️ Agent_Law</div>', unsafe_allow_html=True)
        
        if st.button("💬 Bắt đầu tra cứu mới", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
            
        st.divider()
        
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
        
        st.divider()
        
        st.subheader("Tham Số RAG")
        st.session_state.top_k = st.slider(
            "Điều chỉnh Top-K Context:", 
            min_value=5, max_value=10, 
            value=st.session_state.top_k,
            help="Tăng giá trị này để cung cấp nhiều bối cảnh hơn cho AI, có thể cải thiện độ chính xác nhưng làm chậm tốc độ."
        )
        
        st.divider()
        
        # Lịch sử queries
        st.subheader("📋 Lịch Sử Tra Cứu")
        if st.session_state.history:
            for history_item in reversed(st.session_state.history[-5:]):
                query_text = history_item['query']
                if st.button(f"📜 {query_text[:45]}...", key=f"history_{query_text}", help=query_text):
                    # Khi click, xóa cuộc trò chuyện hiện tại và hiển thị cặp Q&A này
                    st.session_state.messages = [
                        {"role": "user", "content": query_text},
                        {"role": "assistant", "content": history_item['result']}
                    ]
                    st.rerun()
        else:
            st.caption("Lịch sử tra cứu sẽ hiện ở đây.")
    
    # Main content
    st.markdown('<h1 class="main-header">Tra cứu pháp luật - Nhanh chóng & Chính xác với AI</h1>', unsafe_allow_html=True)

    if not st.session_state.data_loaded:
        st.info("""
        ### 📚 Hướng dẫn khởi động hệ thống:
        
        1. **Tải lên file luật (PDF)** bằng công cụ ở thanh menu bên trái.
        2. Nhấp nút **"Xử lý & Nạp Dữ liệu"** để AI tiến hành đọc và ghi nhớ nội dung.
        3. Sau khi có thông báo thành công, bạn có thể bắt đầu **nhập câu hỏi** vào ô chat bên dưới.
        
        *Lưu ý: Hệ thống cũng sẽ tự động nhận diện các file PDF bạn đã đặt sẵn trong thư mục `data`.*
        """)
    else:
        # Hiển thị các tin nhắn trong chat
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.markdown(message["content"])
                else: # assistant
                    render_assistant_response(message["content"])

        # Ô nhập liệu chat
        if prompt := st.chat_input("Nhập tình huống hoặc câu hỏi pháp lý của bạn..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Trợ lý đang lục tìm các văn bản luật và tổng hợp câu trả lời..."):
                    try:
                        # Gọi RAG engine với câu hỏi và giá trị top_k từ slider
                        result = st.session_state.rag_engine.ask_legal_agent(
                            prompt, 
                            top_k=st.session_state.top_k
                        )
                        
                        # Thêm câu trả lời vào lịch sử chat
                        response_message = {"role": "assistant", "content": result}
                        st.session_state.messages.append(response_message)
                        
                        # Thêm vào lịch sử cố định
                        history_item = {"query": prompt, "result": result}
                        # Xóa nếu đã tồn tại để đưa lên đầu
                        st.session_state.history = [h for h in st.session_state.history if h['query'] != prompt]
                        st.session_state.history.append(history_item)
                        
                        # Chạy lại để hiển thị tin nhắn mới
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Xảy ra lỗi: {e}")


if __name__ == "__main__":
    main()