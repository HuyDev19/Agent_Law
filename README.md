# ⚖️ Agent Tra Cứu Luật Pháp Việt Nam

Hệ thống AI Agent cho phép tra cứu thông tin pháp luật Việt Nam bằng ngôn ngữ tự nhiên.  
Ứng dụng công nghệ **RAG (Retrieval-Augmented Generation) v2.0** kết hợp **Google Gemini** để sinh ra câu trả lời chính xác, có căn cứ pháp lý rõ ràng.

---

## 🎯 Tính Năng Chính

| Tính năng | Mô tả |
|-----------|-------|
| 📄 **Đọc PDF Luật** | Tự động load và trích xuất text từ file PDF trong thư mục `data/` |
| ✂️ **Chunking Thông Minh** | Cắt chunk theo cấu trúc Điều → Khoản của luật Việt Nam, có cơ chế Fallback tự động |
| 🔄 **Query Rewriting** | LLM pháp lý hóa câu hỏi trước khi tìm kiếm để tăng độ chính xác retrieval |
| 🔍 **Hybrid Search** | Kết hợp Vector MMR (ngữ nghĩa) + BM25 (từ khóa) qua Reciprocal Rank Fusion |
| 🧠 **Vietnamese SBERT** | Embedding chuyên biệt cho tiếng Việt (`keepitreal/vietnamese-sbert`) |
| 🗄️ **ChromaDB** | Lưu trữ vector cục bộ, tái sử dụng không cần index lại |
| ✨ **Structured Output** | Kết quả luôn có đủ 3 phần: Tóm tắt / Phân tích chi tiết / Căn cứ pháp lý (dạng bảng) |
| 🖥️ **Giao Diện Streamlit** | UI thân thiện, có lịch sử tra cứu và thanh điều chỉnh Top-K |

---

## 📋 Yêu Cầu Hệ Thống

- **Python**: 3.9 trở lên (khuyến nghị 3.11)
- **RAM**: tối thiểu 4 GB (8 GB khuyến nghị)
- **Google Gemini API Key**: Lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## 🚀 Hướng Dẫn Cài Đặt (Từ Đầu)

### Bước 1 — Clone Repository

```bash
git clone <repo_url>
cd Agent_Law
```

### Bước 2 — Tạo Virtual Environment

```bash
python -m venv venv
```

Kích hoạt môi trường ảo:

```bash
# Windows (PowerShell)
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

> Dấu `(venv)` xuất hiện ở đầu dòng terminal nghĩa là đã kích hoạt thành công.

### Bước 3 — Cài Đặt Thư Viện

```bash
pip install -r requirements.txt
```

**Sau đó cài PyTorch CPU riêng** (tránh pip tự kéo bản CUDA nặng hàng GB):

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

> ⏳ Lần đầu cài sẽ mất vài phút. Lần sau chạy lại sẽ nhanh hơn vì đã có cache.

### Bước 4 — Cấu Hình API Key

Tạo file `.env` trong thư mục gốc (hoặc sao chép từ `.env.example`):

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Mở file `.env` và điền API Key của bạn:

```env
GEMINI_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.0
```

**Lấy Gemini API Key miễn phí:**
1. Truy cập [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Nhấp **"Create API Key"**
3. Copy key và dán vào `.env`

### Bước 5 — Thêm File PDF Luật

Đặt các file PDF văn bản pháp luật vào thư mục `data/`:

```
Agent_Law/
└── data/
    ├── Bo_luat_Lao_dong.pdf
    ├── Nghi_dinh_100_2019.pdf
    └── ...
```

> Hệ thống hỗ trợ nhiều file PDF cùng lúc. PDF phải có **text thật** (không phải ảnh scan).

### Bước 6 — Chạy Ứng Dụng

```bash
python -m streamlit run app.py
```

Ứng dụng sẽ tự động mở tại: **`http://localhost:8501`**

---

## 🖥️ Hướng Dẫn Sử Dụng

1. **Lần đầu tiên** — Nhấn nút **"🔄 Nạp Dữ Liệu PDF Mới"** ở sidebar để hệ thống đọc và index các file PDF vào ChromaDB. Quá trình này chỉ cần làm một lần (hoặc khi có file PDF mới).
2. **Lần sau** — Hệ thống tự động kết nối lại dữ liệu đã index từ thư mục `database/`, không cần nạp lại.
3. **Tra cứu** — Nhập câu hỏi bằng tiếng Việt tự nhiên vào ô tìm kiếm, nhấn **"🔎 Trích xuất câu trả lời"**.
4. **Điều chỉnh Top-K** — Dùng thanh trượt ở sidebar để chỉnh số lượng đoạn luật dùng làm bối cảnh (khuyến nghị: 5–7).

---

## 📁 Cấu Trúc Dự Án

```
Agent_Law/
├── data/                    # 📂 Đặt file PDF luật vào đây (tự động tạo khi chạy)
│   └── *.pdf
├── database/                # 🗄️ ChromaDB lưu vector embeddings (tự động tạo)
├── src/
│   ├── __init__.py
│   ├── data_loader.py       # Đọc PDF, làm sạch, cắt chunk theo Điều/Khoản
│   └── rag_engine.py        # RAG Engine v2.0: Hybrid Search, Query Rewriting, LLM
├── .env                     # 🔑 API Keys (bạn tự tạo, KHÔNG commit lên git)
├── .env.example             # Mẫu cấu hình .env
├── .gitignore
├── app.py                   # Streamlit UI — file chạy chính
├── requirements.txt         # Danh sách thư viện Python
└── README.md
```

---

## ⚙️ Kiến Trúc RAG Pipeline v2.0

```
Câu hỏi người dùng
        │
        ▼
[1] Query Rewriting ──► LLM pháp lý hóa câu hỏi
        │
        ▼
[2] Hybrid Search
    ├── Vector MMR Search (60%) ──► ChromaDB
    └── BM25 Keyword Search (40%) ──► Rank BM25
        │
        ▼
    RRF — Reciprocal Rank Fusion
        │
        ▼
[3] Semantic Grouping ──► Gom nhóm: Văn bản → Điều → Khoản
        │
        ▼
[4] LLM Generation (Gemini) + Structured Prompt
        │
        ▼
[5] Kết quả có cấu trúc:
    📋 Tóm tắt
    📖 Phân tích chi tiết
    ⚖️ Căn cứ pháp lý (bảng)
```

---

## 🛠️ Xử Lý Sự Cố Thường Gặp

### ❌ `GEMINI_API_KEY not found`
→ Kiểm tra file `.env` đã tồn tại và có đủ key chưa. Restart ứng dụng sau khi sửa.

### ❌ `No PDFs found in data/`
→ Kiểm tra đã đặt file PDF vào thư mục `data/`. Chỉ hỗ trợ PDF có text, không phải PDF ảnh scan.

### ❌ `ModuleNotFoundError: No module named 'torchvision'`
→ Chạy lệnh sau sau khi kích hoạt venv:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### ❌ Cảnh báo đỏ gạch chân import trong VS Code
→ Nhấn `Ctrl+Shift+P` → **"Python: Select Interpreter"** → chọn `.\venv\Scripts\python.exe`.

### ⚠️ Lần đầu chạy rất chậm (5–15 phút)
→ Hệ thống đang tải model embedding `vietnamese-sbert` từ HuggingFace (~400 MB). Lần sau sẽ dùng cache cục bộ và khởi động trong vài giây.

### ⚠️ Câu trả lời thiếu thông tin
→ Tăng giá trị **Top-K** trong sidebar lên 7–10. Hoặc kiểm tra file PDF có text không bị lỗi encoding.

---

## 🔐 Bảo Mật

- ⚠️ **KHÔNG commit file `.env`** lên git — đã được thêm vào `.gitignore`
- ✅ Dùng `.env.example` để hướng dẫn người dùng mới cấu hình
- ✅ API Key chỉ được đọc qua biến môi trường, không hardcode trong code

---

## 📈 Roadmap

- [ ] Hỗ trợ upload PDF trực tiếp trong giao diện Streamlit
- [ ] Thêm chức năng xuất kết quả ra file Word/PDF
- [ ] Tích hợp thêm nguồn dữ liệu (văn bản luật online)
- [ ] Hỗ trợ hỏi đáp đa lượt (Multi-turn Conversation)
- [ ] Hỗ trợ GPU để tăng tốc embedding

---

## 📜 License

MIT License

---

*⚖️ Hệ thống chỉ mang tính chất tham khảo. Mọi quyết định pháp lý quan trọng cần tham vấn luật sư chuyên nghiệp.*
