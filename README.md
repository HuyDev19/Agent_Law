# ⚖️ Agent Tra Cứu Luật Pháp Việt Nam

Hệ thống AI Agent cho phép tra cứu thông tin pháp luật Việt Nam bằng cách hỏi bằng ngôn ngữ tự nhiên. Sử dụng công nghệ **RAG (Retrieval-Augmented Generation)** kết hợp **Google Gemini API** để sinh ra câu trả lời chính xác.

## 🎯 Tính Năng

- ✅ **Đọc PDF Luật**: Tự động load và xử lý file PDF từ thư mục `data/`
- ✅ **Cắt Chunk Thông Minh**: Chia document theo cấu trúc "Điều X." của luật Việt Nam
- ✅ **Vector Embeddings**: Sử dụng Vietnamese SBERT để hiểu semantic tiếng Việt
- ✅ **Vector Database**: ChromaDB lưu trữ embeddings tối ưu cho tìm kiếm nhanh
- ✅ **LLM Gemini Pro**: Generate response từ context được lấy ra
- ✅ **Giao Diện Streamlit**: UI thân thiện, dễ sử dụng
- ✅ **Trích Dẫn Nguồn**: Tự động cung cấp tham chiếu đến Điều/Bộ luật

## 📋 Yêu Cầu

- Python 3.9+
- Google API Key (Gemini Pro)
- Các thư viện trong `requirements.txt`

## 🚀 Cài Đặt & Hướng Dẫn

### 1. Clone Repository
```bash
git clone <repo_url>
cd Agent_Law
```

### 2. Tạo Virtual Environment
```bash
python -m venv venv

# Trên Windows
venv\Scripts\activate

# Trên macOS/Linux
source venv/bin/activate
```

### 3. Cài Đặt Dependencies
```bash
pip install -r requirements.txt
```

### 4. Cấu Hình API Key
Tạo file `.env` trong thư mục gốc:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

**Lấy API Key**: 
1. Vào https://makersuite.google.com/app/apikey
2. Nhấp "Create API Key"
3. Copy key vào `.env`

### 5. Thêm File PDF
- Đặt các file PDF luật pháp vào thư mục `data/`
- Ví dụ: `data/Bộ_luật_Lao_động.pdf`

### 6. Chạy Ứng Dụng
```bash
streamlit run src/app.py
```

Ứng dụng sẽ mở tại `http://localhost:8501`

## 📁 Cấu Trúc Dự Án

```
Agent_Law/
├── data/                    # PDF files (Tự động tạo)
│   └── *.pdf               # Đặt file PDF tại đây
├── database/               # ChromaDB storage (Tự động tạo)
├── src/
│   ├── __init__.py        # Package init
│   ├── data_loader.py     # Đọc PDF, cắt chunk theo "Điều X."
│   ├── rag_engine.py      # RAG: Embeddings, Vector DB, LLM
│   └── app.py             # Streamlit app (file chạy chính)
├── .env                   # API Keys (bạn phải tạo)
├── .gitignore             # Git ignore rules
├── requirements.txt       # Python dependencies
└── README.md             # File này
```

## 🔧 Cấu Hình Chi Tiết

### data_loader.py
```python
from src.data_loader import LawDataLoader

loader = LawDataLoader(data_path="data")
chunks = loader.process_all_documents()
# Kết quả: List chunks với metadata {"document", "article", "source"}
```

**Cách hoạt động:**
- ✅ Load tất cả PDF trong `data/`
- ✅ Làm sạch text (xóa ký tự lạ, khoảng trắng thừa)
- ✅ Cắt theo regex pattern: `Điều \d+[a-zA-Z]*`
- ✅ Giữ metadata: tên document, số điều, nguồn

### rag_engine.py
```python
from src.rag_engine import RAGEngine

rag = RAGEngine(db_path="database")
rag.add_documents(chunks)

# Tra cứu
response = rag.query("Quyền lao động là gì?", top_k=3)
```

**Các bước:**
1. **Embedding**: Input → GoogleGenerativeAIEmbeddings
2. **Search**: ChromaDB cosine similarity search
3. **Ranking**: Top-k kết quả có relevance cao nhất
4. **Generation**: Gemini Pro tạo response từ context
5. **Citation**: Tự động thêm nguồn tham khảo

### app.py - Streamlit Interface
- **Query Input**: Text area cho câu hỏi
- **Search Button**: Kích hoạt RAG pipeline
- **Response Display**: Hiển thị kết quả + nguồn
- **History**: Lưu lịch sử 5 câu hỏi gần nhất

## 💡 Ví Dụ Sử Dụng

### Câu Hỏi 1: Tìm Điều Cụ Thể
```
Input: Điều 24 Bộ luật Lao động nói về cái gì?
Output: [Nội dung Điều 24 + nguồn]
```

### Câu Hỏi 2: Tìm Kiếm Semantic
```
Input: Quyền nghỉ phép của người lao động?
Output: [Tìm tất cả điều liên quan đến nghỉ phép + context]
```

### Câu Hỏi 3: So Sánh
```
Input: Khác nhau giữa hợp đồng xác định thời hạn và không xác định thời hạn?
Output: [Trích dẫn từ các Điều liên quan + so sánh]
```

## 🛠️ Troubleshooting

### ❌ Lỗi: "GEMINI_API_KEY not found"
**Giải pháp**: 
- Tạo file `.env`
- Thêm `GEMINI_API_KEY=your_key`
- Restart ứng dụng

### ❌ Lỗi: "No PDFs found in data/"
**Giải pháp**:
- Tạo thư mục `data/`
- Đặt file PDF vào
- Nhấp "Tải Dữ Liệu Mới" trong app

### ❌ Lỗi: "ChromaDB connection failed"
**Giải pháp**:
- Kiểm tra `.env` có `CHROMADB_MODE=local`
- Xóa thư mục `database/` và khởi động lại
- Nếu dùng server: `docker run -p 8000:8000 chromadb/chroma`

### ⚠️ Embedding chậm lần đầu tiên
**Giải pháp**: Điều này bình thường (download model)

## 📊 Performance Tips

- **Chunk Size**: Hiện tại = 1 Điều. Nếu cần tối ưu, có thể gộp Điều nhỏ
- **Top-K**: Mặc định 3. Tăng lên 5-10 cho câu hỏi phức tạp
- **Temperature**: Đặt = 0 để sinh response xác định, consistent

## 🔐 Bảo Mật

- ⚠️ **Không commit `.env`** - Đã thêm vào `.gitignore`
- ⚠️ **Bảo vệ API Key** - Dùng biến môi trường, không hardcode
- ✅ **Sử dụng `.env.example`** để hướng dẫn setup (tùy chọn)

## 📈 Mở Rộng Tương Lai

- [ ] Support thêm LLM providers (OpenAI, Claude, vv)
- [ ] Thêm features: feedback, re-ranking
- [ ] Cải thiện chunking logic
- [ ] Hỗ trợ upload PDF trực tiếp trong UI
- [ ] Export kết quả ra PDF/Word
- [ ] Đa ngôn ngữ

## 📜 License

MIT License

## 👤 Tác Giả

Team Development

## 📧 Support

Liên hệ: [support email hoặc issue tracker]

---

**Happy Querying! ⚖️✨**
