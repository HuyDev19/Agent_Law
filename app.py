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

from src.data_loader import LawDataLoader
from src.rag_engine import LegalBrainEngine

# Cấu hình Streamlit
st.set_page_config(
    page_title="Agent Tra Cứu Luật Pháp Việt Nam",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', sans-serif; color: #CBD5E1; }
    footer { visibility: hidden; height: 0; position: absolute; }
    #MainMenu { visibility: hidden; }
    [data-testid="stHeader"] { background-color: #0F172A; }
    [data-testid="stAppViewContainer"] { background-color: #0F172A; }
    [data-testid="stSidebar"] { background-color: #1E293B; border-right: 1px solid #334155; padding: 1.5rem 1rem; }
    .sidebar-logo { font-size: 1.75em; font-weight: 700; color: #F1F5F9; padding-bottom: 1rem; margin-bottom: 1rem; border-bottom: 1px solid #334155; }
    [data-testid="stSidebar"] .stButton > button { background-color: transparent; color: #94A3B8; border: none; text-align: left; font-weight: 500; padding: 0.75rem 0.5rem; border-radius: 0.5rem; width: 100%; transition: background-color 0.2s, color 0.2s; display: flex; align-items: center; }
    [data-testid="stSidebar"] .stButton > button:hover { background-color: #334155; color: #F1F5F9; }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] { background-color: #4F46E5; color: white; font-weight: 600; }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover { background-color: #4338CA; }
    [data-testid="stFileUploader"] { border: 1px solid #334155; background-color: #1E293B; border-radius: 0.5rem; }
    [data-testid="stFileUploader"] label { font-weight: 500; color: #CBD5E1; }
    .main-header { font-size: 2.25em; font-weight: 700; color: #F8FAFC; text-align: center; padding: 1rem 0 2rem 0; }
    [data-testid="stChatInput"] { background-color: #0F172A; }
    .response-card { background-color: #1E293B; border: 1px solid #334155; border-radius: 0.75rem; padding: 1.5rem; margin-top: 1rem; box-shadow: none; }
    .summary-section { background-color: #334155; border: 1px solid #475569; border-radius: 0.5rem; padding: 1rem; margin-bottom: 1.5rem; }
    .response-card h2 { font-size: 1.1em; font-weight: 600; color: #F1F5F9; border-bottom: 1px solid #334155; padding-bottom: 0.5rem; margin-top: 1rem; margin-bottom: 1rem; }
    .response-card h2:first-child { margin-top: 0; }
    [data-testid="stCaption"] { color: #94A3B8; }
    .st-emotion-cache-nahz7x a { color: #818CF8; }
    [data-testid="stAlert"] * { color: #0F172A !important; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    if "rag_engine" not in st.session_state:
        st.session_state.rag_engine = None
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "top_k" not in st.session_state:
        st.session_state.top_k = 5
    if "trigger_query" not in st.session_state:
        st.session_state.trigger_query = None
    if "is_follow_up" not in st.session_state:
        st.session_state.is_follow_up = False


def load_and_index_data():
    with st.spinner("⏳ Đang kiểm tra và nhúng dữ liệu mới vào não AI..."):
        try:
            loader = LawDataLoader(data_path="data")
            chunks, new_files = loader.process_all_documents()
            if st.session_state.rag_engine is None:
                rag_engine = LegalBrainEngine(db_path="database")
                if os.path.exists("database") and os.listdir("database"):
                    rag_engine.load_existing_db()
                st.session_state.rag_engine = rag_engine
                st.session_state.data_loaded = True
            if not chunks:
                if st.session_state.data_loaded:
                    st.info("✅ Dữ liệu hiện tại đã được đồng bộ.")
                else:
                    st.warning("⚠️ Không tìm thấy file PDF nào trong thư mục `data/`.")
                return True
            st.session_state.rag_engine.create_vector_db(chunks)
            loader.mark_as_processed(new_files)
            st.session_state.data_loaded = True
            st.success(f"✅ Đã tải và indexing {len(chunks)} phân đoạn thành công!")
            return True
        except Exception as e:
            st.error(f"❌ Lỗi xử lý dữ liệu: {str(e)}")
            return False


def render_assistant_response(result: dict, is_latest: bool = False, msg_index: int = 0):
    answer = result.get("answer", "Không có câu trả lời.")
    sources = result.get("sources", [])

    if isinstance(answer, list):
        parsed_chunks = []
        for chunk in answer:
            if isinstance(chunk, dict):
                parsed_chunks.append(chunk.get('text', ''))
            elif hasattr(chunk, 'text'):
                parsed_chunks.append(chunk.text)
            else:
                parsed_chunks.append(str(chunk))
        answer = "".join(parsed_chunks)
    elif isinstance(answer, dict):
        answer = answer.get('text', str(answer))
    elif not isinstance(answer, str):
        answer = str(answer)
        
    answer = answer.replace('\\n', '\n')

    suggest_text = ""
    suggest_match = re.search(r'(?i)#+\s*💡?\s*CÂU HỎI GỢI Ý(.*?)$', answer, re.DOTALL)
    if suggest_match:
        suggest_text = suggest_match.group(1).strip()
        answer = answer[:suggest_match.start()].strip()

    with st.container():
        st.markdown('<div class="response-card">', unsafe_allow_html=True)
        
        parts = re.split(r'(?i)#+\s*(?:📋?\s*TÓM TẮT|📖?\s*PHÂN TÍCH CHI TIẾT|⚖️?\s*CĂN CỨ PHÁP LÝ)', answer)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) > 0:
            st.markdown('<h2>📋 TÓM TẮT</h2>', unsafe_allow_html=True)
            summary_html = f'<div class="summary-section">{parts[0]}</div>'
            st.markdown(summary_html, unsafe_allow_html=True)
        if len(parts) > 1:
            st.markdown('<h2>📖 PHÂN TÍCH CHI TIẾT</h2>', unsafe_allow_html=True)
            st.markdown(parts[1], unsafe_allow_html=True)
        if len(parts) > 2:
            st.markdown('<h2>⚖️ CĂN CỨ PHÁP LÝ</h2>', unsafe_allow_html=True)
            st.markdown(parts[2], unsafe_allow_html=True)

        if suggest_text and is_latest:
            questions = [q.strip().lstrip('-').lstrip('•').strip() for q in suggest_text.split('\n')]
            questions = [q for q in questions if q and len(q) > 5]
            if questions:
                st.markdown('<p style="font-weight: 600; color: #818CF8; margin-top: 1.5rem; margin-bottom: 0.5rem;">💡 Có thể bạn muốn hỏi tiếp:</p>', unsafe_allow_html=True)
                for j, q in enumerate(questions[:3]):
                    if st.button(f"✨ {q}", key=f"sugg_{msg_index}_{j}", help="Nhấp để hỏi ngay"):
                        st.session_state.trigger_query = q
                        st.session_state.is_follow_up = True 
                        st.rerun()

        if sources:
            st.markdown('<div class="source-citation" style="padding-top: 1.5rem; font-size: 0.9em;">', unsafe_allow_html=True)
            st.markdown('<p style="font-weight: 600; color: #E2E8F0;">📂 Văn bản căn cứ trích xuất:</p>', unsafe_allow_html=True)
            for source in sources:
                st.caption(f"• {source}")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def main():
    init_session_state()
    if st.session_state.rag_engine is None:
        if os.path.exists("database") and os.listdir("database"):
            try:
                rag_engine = LegalBrainEngine(db_path="database")
                if rag_engine.load_existing_db():
                    st.session_state.rag_engine = rag_engine
                    st.session_state.data_loaded = True
            except Exception: pass
    
    with st.sidebar:
        st.markdown('<div class="sidebar-logo">⚖️ Agent_Law</div>', unsafe_allow_html=True)
        if st.button("💬 Bắt đầu tra cứu mới", use_container_width=True):
            st.session_state.messages = []
            st.session_state.trigger_query = None
            st.session_state.is_follow_up = False
            st.rerun()
        st.divider()
        if not os.getenv("GEMINI_API_KEY"): st.error("❌ Chưa cấu hình API Key"); st.stop()
        else: st.success("✅ Đã kết nối API Gemini")
        st.divider()
        uploaded_files = st.file_uploader("Tải lên PDF:", type="pdf", accept_multiple_files=True)
        if st.button("🔄 Xử lý dữ liệu", use_container_width=True, type="primary"):
            if uploaded_files:
                data_path = Path("data")
                data_path.mkdir(exist_ok=True)
                for uploaded_file in uploaded_files:
                    with open(data_path / uploaded_file.name, "wb") as f: f.write(uploaded_file.getbuffer())
            load_and_index_data(); st.rerun()
        st.divider()
        st.session_state.top_k = st.slider("Top-K Context:", 5, 10, st.session_state.top_k)
    
    st.markdown('<h1 class="main-header">Tra cứu pháp luật với AI</h1>', unsafe_allow_html=True)

    if not st.session_state.data_loaded:
        st.info("### 📚 Hướng dẫn: Tải PDF và nhấn Xử lý dữ liệu.")
    else:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                if message["role"] == "user": st.markdown(message["content"])
                else: render_assistant_response(message["content"], is_latest=(i == len(st.session_state.messages) - 1), msg_index=i)

        user_input = st.chat_input("Nhập câu hỏi pháp lý...")
        if user_input:
            st.session_state.trigger_query = user_input
            st.session_state.is_follow_up = False 

        prompt = st.session_state.trigger_query

        if prompt:
            chat_context = ""
            if st.session_state.is_follow_up and len(st.session_state.messages) >= 2:
                last_q = st.session_state.messages[-2]["content"]
                last_a_data = st.session_state.messages[-1]["content"]
                last_a_text = last_a_data.get("answer", "") if isinstance(last_a_data, dict) else str(last_a_data)
                chat_context = f"- Câu hỏi trước: {last_q}\n- Trả lời trước: {last_a_text[:1500]}"

            st.session_state.trigger_query = None
            st.session_state.is_follow_up = False

            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🤖 Đang tư vấn..."):
                    try:
                        result = st.session_state.rag_engine.ask_legal_agent(prompt, top_k=st.session_state.top_k, chat_context=chat_context)
                        st.session_state.messages.append({"role": "assistant", "content": result})
                        st.session_state.history.append({"query": prompt, "result": result})
                        st.rerun()
                    except Exception as e: st.error(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    main()