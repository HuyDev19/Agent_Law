"""
Agent_Law — Streamlit App v3.0
Giao diện Premium cho AI Agent Tra cứu Luật pháp Việt Nam
=========================================================
Import logic: src/rag_engine.LegalBrainEngine.ask_legal_agent()
Import loader: src/data_loader.LawDataLoader.process_all_documents()
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

import streamlit as st

# ─── Load biến môi trường ───────────────────────────────────────────────────
load_dotenv()

# ─── Import logic gốc (KHÔNG thay đổi) ─────────────────────────────────────
from src.data_loader import LawDataLoader
from src.rag_engine import LegalBrainEngine


# ════════════════════════════════════════════════════════════════════════════
# CACHE_RESOURCE — Khởi tạo engine CHỈ 1 LẦN cho toàn bộ vòng đời server
# @st.cache_resource giữ object trong RAM, mọi rerun đều dùng lại bản này.
# ════════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def _get_engine(db_path: str = "database") -> LegalBrainEngine:
    """Singleton: tạo LegalBrainEngine một lần, cache mãi mãi."""
    return LegalBrainEngine(db_path=db_path)

# ════════════════════════════════════════════════════════════════════════════
# CẤU HÌNH TRANG
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Agent_Law — Tư vấn Pháp luật AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS — Dark Mode · Glassmorphism · Animations · Premium Typography
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root tokens ── */
:root {
    --bg-base:       #060B18;
    --bg-surface:    #0D1526;
    --bg-card:       #111D35;
    --bg-hover:      #1A2B4A;
    --border:        rgba(99,179,237,0.12);
    --border-accent: rgba(99,179,237,0.3);
    --accent:        #3B82F6;
    --accent-glow:   rgba(59,130,246,0.25);
    --accent2:       #8B5CF6;
    --accent2-glow:  rgba(139,92,246,0.2);
    --gold:          #F59E0B;
    --green:         #10B981;
    --red:           #EF4444;
    --text-primary:  #F0F6FF;
    --text-secondary:#94A3B8;
    --text-muted:    #475569;
    --radius-sm:     8px;
    --radius-md:     14px;
    --radius-lg:     20px;
    --shadow-glow:   0 0 30px rgba(59,130,246,0.15);
    --transition:    all 0.25s cubic-bezier(0.4,0,0.2,1);
}

/* ── Base layout ── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg-base) !important;
    font-family: 'Inter', sans-serif !important;
    color: var(--text-primary) !important;
}
[data-testid="stHeader"]   { background: transparent !important; border: none !important; }
footer, #MainMenu          { visibility: hidden !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
    padding: 0 !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1.25rem 2rem !important; }

/* ── Sidebar buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: 1px solid transparent !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 500 !important;
    text-align: left !important;
    width: 100% !important;
    padding: 0.6rem 0.9rem !important;
    transition: var(--transition) !important;
    font-size: 0.88rem !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-hover) !important;
    color: var(--text-primary) !important;
    border-color: var(--border-accent) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: var(--shadow-glow) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 0 40px rgba(59,130,246,0.35) !important;
}

/* ── Main area ── */
[data-testid="stMain"] { padding: 0 !important; }
.block-container { padding: 2rem 2.5rem !important; max-width: 1100px !important; margin: 0 auto !important; }

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-accent) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    transition: var(--transition) !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0.25rem 0 !important;
}

/* ── Alerts ── */
[data-testid="stAlert"]            { border-radius: var(--radius-md) !important; }
[data-testid="stAlert"][data-baseweb="notification"] { background: rgba(16,185,129,0.1) !important; border: 1px solid rgba(16,185,129,0.3) !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--bg-card) !important;
    border: 1px dashed var(--border-accent) !important;
    border-radius: var(--radius-md) !important;
    padding: 0.5rem !important;
    transition: var(--transition) !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--accent) !important; }
[data-testid="stFileUploader"] label { color: var(--text-secondary) !important; font-size: 0.85rem !important; }

/* ── Slider ── */
[data-testid="stSlider"] .st-emotion-cache-1dx1gwv { color: var(--accent) !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] > div { border-color: var(--accent) !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

/* ── Caption ── */
[data-testid="stCaption"] { color: var(--text-muted) !important; font-size: 0.8rem !important; }

/* ── CUSTOM COMPONENTS ── */

/* Hero header */
.hero-header {
    text-align: center;
    padding: 2.5rem 0 2rem;
    position: relative;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.3);
    border-radius: 50px;
    padding: 0.35rem 1rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: #60A5FA;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.hero-title {
    font-size: clamp(1.6rem, 3vw, 2.4rem);
    font-weight: 800;
    background: linear-gradient(135deg, #F0F6FF 0%, #93C5FD 50%, #A78BFA 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.5rem;
    line-height: 1.2;
}
.hero-subtitle {
    color: var(--text-secondary);
    font-size: 1rem;
    font-weight: 400;
    max-width: 600px;
    margin: 0 auto;
}

/* Sidebar logo */
.sidebar-logo {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding-bottom: 1.25rem;
    margin-bottom: 1.25rem;
    border-bottom: 1px solid var(--border);
}
.sidebar-logo-icon {
    font-size: 1.6rem;
    filter: drop-shadow(0 0 8px rgba(59,130,246,0.5));
}
.sidebar-logo-text {
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}
.sidebar-logo-version {
    font-size: 0.65rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 600;
}
.sidebar-section-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 0.75rem 0 0.4rem;
}
.status-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    font-size: 0.82rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
}
.status-badge.ok  { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25); color: #34D399; }
.status-badge.err { background: rgba(239,68,68,0.1);  border: 1px solid rgba(239,68,68,0.25);  color: #F87171; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.status-dot.green { background: #10B981; box-shadow: 0 0 6px #10B981; animation: pulse-green 2s infinite; }
.status-dot.red   { background: #EF4444; }
@keyframes pulse-green {
    0%,100% { box-shadow: 0 0 4px #10B981; }
    50%      { box-shadow: 0 0 12px #10B981; }
}

/* PDF list items */
.pdf-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    color: var(--text-secondary);
    padding: 0.25rem 0;
}
.pdf-item-icon { color: var(--accent); flex-shrink: 0; }

/* Response card */
.resp-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.75rem;
    margin-top: 0.5rem;
    position: relative;
    overflow: hidden;
    animation: fadeSlideIn 0.4s ease-out;
}
.resp-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
}
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Section headers inside response */
.resp-section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0 0 0.75rem;
    border-bottom: 1px solid var(--border);
    margin: 1.25rem 0 1rem;
}
.resp-section-header:first-child { margin-top: 0; }

/* Summary block */
.summary-block {
    background: rgba(59,130,246,0.06);
    border: 1px solid rgba(59,130,246,0.15);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
    margin-bottom: 0.25rem;
    font-size: 0.97rem;
    line-height: 1.7;
    color: var(--text-primary);
}

/* Source tags */
.source-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(139,92,246,0.1);
    border: 1px solid rgba(139,92,246,0.25);
    border-radius: 6px;
    padding: 0.25rem 0.6rem;
    font-size: 0.75rem;
    font-weight: 500;
    color: #C4B5FD;
    margin: 0.2rem 0.2rem 0.2rem 0;
}

/* Suggestion buttons */
.sugg-container { margin-top: 1.25rem; }
.sugg-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.6rem;
}

/* Query rewrite pill */
.rewrite-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.2);
    border-radius: 50px;
    padding: 0.2rem 0.75rem;
    font-size: 0.75rem;
    color: #FCD34D;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 1rem;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-muted);
}
.empty-state-icon { font-size: 3.5rem; margin-bottom: 1rem; opacity: 0.6; }
.empty-state-title { font-size: 1.1rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem; }
.empty-state-desc  { font-size: 0.88rem; line-height: 1.6; }

/* Stats bar */
.stats-bar {
    display: flex;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.25rem;
}
.stat-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    color: var(--text-muted);
}
.stat-value { font-weight: 600; color: var(--text-secondary); }

/* Quick conclusion block */
.conclusion-block {
    background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(59,130,246,0.06));
    border: 1px solid rgba(16,185,129,0.25);
    border-left: 3px solid var(--green);
    border-radius: var(--radius-sm);
    padding: 0.85rem 1.25rem;
    font-size: 1rem;
    font-weight: 500;
    line-height: 1.65;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}

/* Sanction block */
.sanction-block {
    background: rgba(239,68,68,0.05);
    border: 1px solid rgba(239,68,68,0.18);
    border-left: 3px solid #EF4444;
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
    font-size: 0.95rem;
    line-height: 1.7;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}

/* Case law block */
.caselaw-block {
    background: rgba(245,158,11,0.05);
    border: 1px solid rgba(245,158,11,0.18);
    border-left: 3px solid var(--gold);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
    font-size: 0.95rem;
    line-height: 1.7;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
}

/* Section header color variants */
.resp-section-header.green  { color: #34D399; }
.resp-section-header.red    { color: #F87171; }
.resp-section-header.gold   { color: #FCD34D; }
.resp-section-header.purple { color: #C4B5FD; }

/* User message bubble */
.user-bubble {
    background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.1));
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: var(--radius-md) var(--radius-md) 4px var(--radius-md);
    padding: 0.85rem 1.1rem;
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--text-primary);
    margin-left: auto;
    max-width: 85%;
    animation: fadeSlideIn 0.3s ease-out;
}

/* Thinking indicator */
.thinking-dots {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.5rem 0;
}
.thinking-dots span {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent);
    animation: bounce 1.4s infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
    0%,80%,100% { transform: scale(0.6); opacity: 0.4; }
    40%          { transform: scale(1);   opacity: 1; }
}
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════════════
def _init_state():
    defaults = {
        "rag_engine":    None,
        "data_loaded":   False,
        "messages":      [],
        "history":       [],
        "top_k":         8,
        "trigger_query": None,
        "is_follow_up":  False,
        "indexed_pdfs":  [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ════════════════════════════════════════════════════════════════════════════
# KHỞI TẠO RAG ENGINE (TỰ ĐỘNG KHI CÓ DATABASE SẴN)
# Dùng _get_engine() đã cache — KHÔNG tạo object mới mỗi rerun
# ════════════════════════════════════════════════════════════════════════════
def _auto_load_engine():
    """Lấy engine từ cache; nếu có DB sẵn thì load vào engine."""
    # Lấy singleton engine từ cache (lần đầu mới tạo, sau dùng lại)
    engine = _get_engine(db_path="database")

    if st.session_state.rag_engine is not None:
        return  # Đã gắn vào session, bỏ qua

    if os.path.exists("database") and os.listdir("database"):
        try:
            if engine.load_existing_db():
                st.session_state.rag_engine = engine
                st.session_state.data_loaded = True
                # Đọc danh sách PDF đã index
                tracking = Path("data/processed_files.json")
                if tracking.exists():
                    import json
                    with open(tracking, encoding="utf-8") as f:
                        st.session_state.indexed_pdfs = json.load(f)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
# XỬ LÝ DỮ LIỆU PDF
# ════════════════════════════════════════════════════════════════════════════
def _process_pdfs(uploaded_files=None) -> bool:
    """Lưu PDF upload → chạy LawDataLoader → tạo Vector DB."""
    with st.spinner("⚙️ Đang phân tích và nhúng dữ liệu vào não AI..."):
        try:
            # Lưu file upload vào disk
            if uploaded_files:
                data_dir = Path("data")
                data_dir.mkdir(exist_ok=True)
                for f in uploaded_files:
                    with open(data_dir / f.name, "wb") as fp:
                        fp.write(f.getbuffer())

            # Chạy loader (không thay đổi logic gốc)
            loader = LawDataLoader(data_path="data")
            chunks, new_files = loader.process_all_documents()

            # Lấy engine từ cache (không tạo mới)
            if st.session_state.rag_engine is None:
                engine = _get_engine(db_path="database")
                if os.path.exists("database") and os.listdir("database"):
                    engine.load_existing_db()
                st.session_state.rag_engine = engine

            if chunks:
                st.session_state.rag_engine.create_vector_db(chunks)
                loader.mark_as_processed(new_files)
                st.session_state.indexed_pdfs.extend(new_files)

            st.session_state.data_loaded = True
            return True, len(chunks), len(new_files)
        except Exception as e:
            return False, 0, str(e)


# ════════════════════════════════════════════════════════════════════════════
# RENDER: SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────
        st.markdown("""
        <div class="sidebar-logo">
          <span class="sidebar-logo-icon">⚖️</span>
          <div>
            <div class="sidebar-logo-text">Agent_Law</div>
            <div class="sidebar-logo-version">✦ Powered by Gemini + RAG v3.0</div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── Trạng thái API ─────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">🔌 Kết nối</div>', unsafe_allow_html=True)
        if os.getenv("GEMINI_API_KEY"):
            st.markdown('<div class="status-badge ok"><div class="status-dot green"></div>Đã kết nối Gemini API</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge err"><div class="status-dot red"></div>Chưa cấu hình API Key</div>', unsafe_allow_html=True)
            st.caption("Thêm GEMINI_API_KEY vào file `.env`")
            st.stop()

        # ── Trạng thái dữ liệu ─────────────────────────────────────────────
        if st.session_state.data_loaded:
            st.markdown(f'<div class="status-badge ok"><div class="status-dot green"></div>Kho dữ liệu đã sẵn sàng</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge err"><div class="status-dot red"></div>Chưa có dữ liệu</div>', unsafe_allow_html=True)

        st.divider()

        # ── Upload PDF ──────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">📄 Dữ liệu văn bản luật</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Tải lên file PDF luật:",
            type="pdf",
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="pdf_uploader"
        )
        if st.button("🔄 Xử lý & Nạp vào hệ thống", use_container_width=True, type="primary"):
            result = _process_pdfs(uploaded)
            ok = result[0]
            if ok:
                n_chunks = result[1]
                n_files  = result[2]
                if n_chunks > 0:
                    st.success(f"✅ {n_files} file mới · {n_chunks} phân đoạn")
                else:
                    st.info("✅ Dữ liệu đã đồng bộ, không có file mới.")
            else:
                st.error(f"❌ Lỗi: {result[2]}")
            st.rerun()

        # Danh sách PDF đã index
        if st.session_state.indexed_pdfs:
            st.markdown('<div class="sidebar-section-label" style="margin-top:0.75rem">📚 Văn bản đã nạp</div>', unsafe_allow_html=True)
            for pdf_name in st.session_state.indexed_pdfs[:12]:
                display = pdf_name.replace(".pdf","").replace("_"," ")[:32]
                st.markdown(f'<div class="pdf-item"><span class="pdf-item-icon">📎</span>{display}</div>', unsafe_allow_html=True)
            if len(st.session_state.indexed_pdfs) > 12:
                st.caption(f"... và {len(st.session_state.indexed_pdfs)-12} văn bản khác")

        st.divider()

        # ── Cài đặt truy vấn ───────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">⚙️ Tham số truy vấn</div>', unsafe_allow_html=True)
        st.session_state.top_k = st.slider(
            "Top-K ngữ cảnh truy xuất:",
            min_value=3, max_value=12,
            value=st.session_state.top_k,
            help="Số lượng đoạn văn bản được lấy ra để phân tích. Cao hơn = toàn diện hơn, chậm hơn."
        )

        st.divider()

        # ── Hành động ──────────────────────────────────────────────────────
        st.markdown('<div class="sidebar-section-label">🗂️ Phiên làm việc</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💬 Chat mới", use_container_width=True):
                st.session_state.messages      = []
                st.session_state.trigger_query = None
                st.session_state.is_follow_up  = False
                st.rerun()
        with col2:
            if st.button("📋 Lịch sử", use_container_width=True):
                st.session_state["show_history"] = not st.session_state.get("show_history", False)
                st.rerun()

        # ── Lịch sử truy vấn ───────────────────────────────────────────────
        if st.session_state.get("show_history") and st.session_state.history:
            st.markdown('<div class="sidebar-section-label">📖 Câu hỏi gần đây</div>', unsafe_allow_html=True)
            for i, h in enumerate(reversed(st.session_state.history[-8:])):
                q = h["query"][:55] + "…" if len(h["query"]) > 55 else h["query"]
                if st.button(f"↩ {q}", key=f"hist_{i}", use_container_width=True):
                    st.session_state.trigger_query = h["query"]
                    st.session_state.is_follow_up  = False
                    st.rerun()

        # ── Footer ──────────────────────────────────────────────────────────
        st.markdown("""
        <div style="position:fixed; bottom:1rem; left:0; width:260px; text-align:center; 
                    font-size:0.7rem; color:var(--text-muted); padding:0 1.25rem;">
            RAG v3.0 · Hybrid Search · Web Fallback<br/>
            <span style="color:var(--accent)">⚖️</span> Agent_Law — DH_GTVT_HCM
        </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# RENDER: PHẢN HỒI TRỢ LÝ
# ════════════════════════════════════════════════════════════════════════════
def render_response(result: dict, is_latest: bool = False, msg_index: int = 0):
    """Render câu trả lời từ ask_legal_agent() với layout đẹp, có sections."""
    answer          = result.get("answer", "Không có câu trả lời.")
    sources         = result.get("sources", [])
    rewritten_query = result.get("rewritten_query", "")

    # ── Chuẩn hóa answer ────────────────────────────────────────────────────
    if isinstance(answer, list):
        chunks = []
        for chunk in answer:
            if isinstance(chunk, dict): chunks.append(chunk.get("text", ""))
            elif hasattr(chunk, "text"): chunks.append(chunk.text)
            else: chunks.append(str(chunk))
        answer = "".join(chunks)
    elif isinstance(answer, dict):
        answer = answer.get("text", str(answer))
    elif not isinstance(answer, str):
        answer = str(answer)
    answer = answer.replace("\\n", "\n")

    # ── Tách phần gợi ý ─────────────────────────────────────────────────────
    suggest_text = ""
    suggest_match = re.search(r"(?i)#+\s*💡?\s*CÂU HỎI GỢI Ý(.*?)$", answer, re.DOTALL)
    if suggest_match:
        suggest_text = suggest_match.group(1).strip()
        answer = answer[:suggest_match.start()].strip()

    # ── Card chứa toàn bộ response ──────────────────────────────────────────
    st.markdown('<div class="resp-card">', unsafe_allow_html=True)

    # Query rewritten pill
    if rewritten_query and rewritten_query != st.session_state.messages[-2]["content"] if len(st.session_state.messages) >= 2 else True:
        short_q = rewritten_query[:80] + "…" if len(rewritten_query) > 80 else rewritten_query
        st.markdown(f'<div class="rewrite-pill">🔄 Query pháp lý hóa: {short_q}</div>', unsafe_allow_html=True)

    # ── Tách sections TÓM TẮT / PHÂN TÍCH / CĂN CỨ ─────────────────────────
    parts = re.split(r"(?i)#+\s*(?:📋?\s*TÓM TẮT|📖?\s*PHÂN TÍCH CHI TIẾT|⚖️?\s*CĂN CỨ PHÁP LÝ)", answer)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 1:
        st.markdown('<div class="resp-section-header">📋 TÓM TẮT</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-block">{parts[0]}</div>', unsafe_allow_html=True)

    if len(parts) >= 2:
        st.markdown('<div class="resp-section-header">📖 PHÂN TÍCH CHI TIẾT</div>', unsafe_allow_html=True)
        st.markdown(parts[1], unsafe_allow_html=False)

    if len(parts) >= 3:
        st.markdown('<div class="resp-section-header">⚖️ CĂN CỨ PHÁP LÝ</div>', unsafe_allow_html=True)
        st.markdown(parts[2], unsafe_allow_html=False)

    if len(parts) == 1 and len(parts[0]) < 50:
        # Trường hợp câu trả lời ngắn (DB trống, thông báo lỗi…)
        st.markdown(parts[0] if parts else answer, unsafe_allow_html=False)

    # ── Câu hỏi gợi ý (chỉ hiện cho tin nhắn mới nhất) ─────────────────────
    if suggest_text and is_latest:
        questions = [q.strip().lstrip("-•").strip() for q in suggest_text.split("\n")]
        questions = [q for q in questions if q and len(q) > 8][:3]
        if questions:
            st.markdown('<div class="sugg-container"><div class="sugg-label">💡 Có thể bạn muốn hỏi tiếp</div>', unsafe_allow_html=True)
            for j, q in enumerate(questions):
                if st.button(f"✨ {q}", key=f"sugg_{msg_index}_{j}", help="Nhấp để hỏi ngay"):
                    st.session_state.trigger_query = q
                    st.session_state.is_follow_up  = True
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Nguồn trích dẫn ─────────────────────────────────────────────────────
    if sources:
        st.markdown('<div class="resp-section-header" style="margin-top:1.5rem">📂 Văn bản căn cứ</div>', unsafe_allow_html=True)
        tags_html = "".join(
            f'<span class="source-tag">📎 {s}</span>' for s in sources
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    _init_state()
    _auto_load_engine()
    render_sidebar()

    # ── Hero header ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-header">
      <div class="hero-badge">⚖️ AI Legal Assistant · Vietnam Law</div>
      <h1 class="hero-title">Tra cứu Pháp luật với Trí tuệ Nhân tạo</h1>
      <p class="hero-subtitle">
        Hệ thống RAG nâng cao · Hybrid Search · Web Fallback · Được thiết kế 
        riêng cho văn bản Luật Việt Nam
      </p>
    </div>""", unsafe_allow_html=True)

    # ── Stats bar ────────────────────────────────────────────────────────────
    n_conv   = len(st.session_state.messages) // 2
    n_indexed = len(st.session_state.indexed_pdfs)
    st.markdown(f"""
    <div class="stats-bar">
      <div class="stat-item">💬 <span class="stat-value">{n_conv}</span>&nbsp;câu hỏi trong phiên</div>
      <div class="stat-item">📚 <span class="stat-value">{n_indexed}</span>&nbsp;văn bản đã index</div>
      <div class="stat-item">🔍 <span class="stat-value">Top-{st.session_state.top_k}</span>&nbsp;ngữ cảnh</div>
      <div class="stat-item">🌐 <span class="stat-value">Web Fallback</span>&nbsp;bật</div>
    </div>""", unsafe_allow_html=True)

    # ── EMPTY STATE ──────────────────────────────────────────────────────────
    if not st.session_state.data_loaded:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-state-icon">📚</div>
          <div class="empty-state-title">Kho dữ liệu chưa được kích hoạt</div>
          <div class="empty-state-desc">
            Hãy tải file PDF văn bản luật lên từ thanh bên trái,<br/>
            sau đó nhấn <strong>Xử lý &amp; Nạp vào hệ thống</strong> để bắt đầu.
          </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── RENDER LỊCH SỬ CHAT ──────────────────────────────────────────────────
    for i, msg in enumerate(st.session_state.messages):
        role = msg["role"]
        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            with st.chat_message("assistant", avatar="⚖️"):
                render_response(
                    msg["content"],
                    is_latest=(i == len(st.session_state.messages) - 1),
                    msg_index=i
                )

    # ── CHAT INPUT ───────────────────────────────────────────────────────────
    user_input = st.chat_input(
        placeholder="Nhập câu hỏi pháp lý... (VD: Mức phạt cho hành vi vi phạm bản quyền phần mềm?)",
    )
    if user_input:
        st.session_state.trigger_query = user_input
        st.session_state.is_follow_up  = False

    # ── XỬ LÝ PROMPT (bao gồm cả câu hỏi từ nút gợi ý) ────────────────────
    prompt = st.session_state.trigger_query
    if not prompt:
        return

    # Xây dựng chat_context cho câu hỏi follow-up
    chat_context = ""
    if st.session_state.is_follow_up and len(st.session_state.messages) >= 2:
        last_q      = st.session_state.messages[-2]["content"]
        last_a_data = st.session_state.messages[-1]["content"]
        last_a_text = (
            last_a_data.get("answer", "") if isinstance(last_a_data, dict)
            else str(last_a_data)
        )
        chat_context = f"- Câu hỏi trước: {last_q}\n- Trả lời trước: {last_a_text[:1500]}"

    # Reset trigger
    st.session_state.trigger_query = None
    st.session_state.is_follow_up  = False

    # Thêm tin nhắn user vào lịch sử và hiển thị ngay
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(f'<div class="user-bubble">{prompt}</div>', unsafe_allow_html=True)

    # Gọi hàm logic cốt lõi (KHÔNG thay đổi)
    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("🤖 Bộ não AI đang phân tích văn bản pháp lý..."):
            try:
                # ► ĐÂY LÀ ĐIỂM DUY NHẤT GỌI LOGIC CỐT LÕI ◄
                result = st.session_state.rag_engine.ask_legal_agent(
                    question=prompt,
                    top_k=st.session_state.top_k,
                    chat_context=chat_context,
                )
                st.session_state.messages.append({"role": "assistant", "content": result})
                st.session_state.history.append({"query": prompt, "result": result})
                st.rerun()
            except Exception as e:
                st.error(f"❌ Có lỗi xảy ra trong quá trình xử lý: {e}")


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()