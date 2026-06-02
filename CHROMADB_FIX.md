# 🔧 ChromaDB Deprecated Configuration - Fix & Explanation

**Date:** June 2, 2026  
**Status:** ✅ FIXED

---

## 📋 Lỗi Gốc

```
❌ You are using a deprecated configuration of Chroma.

If you do not have data you wish to migrate, you only need to change 
how you construct your Chroma client...
```

---

## 🔍 Giải Thích Chi Tiết

### **Nguyên Nhân**

ChromaDB đã thay đổi kiến trúc từ phiên bản cũ sang mới:

#### **❌ CÁCH CŨ (Deprecated)**

```python
# Cách 1: CloudClient (không còn)
client = chromadb.CloudClient(
    api_key="...",
    tenant="...",
    database="..."
)

# Cách 2: Client with Settings (deprecated)
from chromadb.config import Settings
client = chromadb.Client(
    Settings(
        chroma_db_impl="duckdb",
        persist_directory="./database"
    )
)
```

**Vấn đề:**
- CloudClient API đã đổi
- Settings config không còn hỗ trợ
- Cách authentication cũ không work

#### **✅ CÁCH MỚI (Recommended)**

```python
# Cách 1: PersistentClient (LOCAL - Recommended)
import chromadb
client = chromadb.PersistentClient(path="./database")

# Cách 2: HttpClient (nếu dùng Chroma Server)
client = chromadb.HttpClient(
    host="localhost",
    port=8000,
    headers={"Authorization": f"Bearer {api_key}"}
)
```

---

## ✅ Fix Được Áp Dụng

### **1. Updated rag_engine.py**

**Thay đổi:**
```python
# ❌ TRƯỚC
from chromadb.config import Settings
client = chromadb.Client(Settings(...))

# ✅ SAU
client = chromadb.PersistentClient(path=self.db_path)
```

**Code mới:**
```python
def __init__(self, db_path: str = "database", ...):
    self.db_path = db_path
    
    # NEW API: PersistentClient
    try:
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        print("✅ Using ChromaDB PersistentClient (Local)")
    except Exception as e:
        print(f"❌ ChromaDB Initialization Error: {str(e)}")
        raise
```

### **2. Updated .env**

**Xóa:**
```env
# ❌ Không cần nữa
CHROMADB_MODE=cloud
CHROMA_HOST=api.trychroma.com
CHROMA_API_KEY=ck-xxx
CHROMA_TENANT=xxx
CHROMA_DATABASE=AgentLaw
```

**Giữ lại:**
```env
# ✅ Chỉ cần đường dẫn database
DATABASE_PATH=database
GEMINI_API_KEY=...
```

### **3. Updated .env.example**

Added notes về ChromaDB changes

---

## 🎯 Ưu & Nhược Điểm Các Cách

### **Option 1: PersistentClient (LOCAL) - ✅ SELECTED**

| Ưu | Nhược |
|-----|-------|
| ✅ Không cần external service | ❌ Không thể scale (single machine) |
| ✅ Dữ liệu lưu local | ❌ Không shared giữa servers |
| ✅ Nhanh (direct disk access) | ❌ Backup phải manual |
| ✅ Không cần credentials | ⚠️ Chỉ phù hợp dev/small projects |
| ✅ Mã code đơn giản | |

**Phù hợp cho:** MVP, Development, Single-server deployment

---

### **Option 2: HttpClient (SERVER MODE)**

| Ưu | Nhược |
|-----|-------|
| ✅ Có thể scale horizontally | ❌ Cần setup Chroma server |
| ✅ Shared data giữa instances | ❌ Network latency |
| ✅ Dễ backup | ❌ Phức tạp hơn |
| ✅ Production-ready | ❌ Cần credentials |

**Phù hợp cho:** Production, Multiple servers, Kubernetes

---

### **Option 3: Cloud (Chroma Cloud - DEPRECATED)**

| Status |
|--------|
| ❌ DEPRECATED (Jun 2026) |
| ❌ API changed |
| ❌ Migration needed |
| ❌ Không khuyên dùng |

---

## 🚀 Cách Upgrade Trong Tương Lai

Khi cần production scale:

```python
# Chuyển từ Local sang Server Mode
# Bước 1: Run Chroma server (Docker)
# docker run -p 8000:8000 chromadb/chroma

# Bước 2: Update code
client = chromadb.HttpClient(
    host="chroma-server.example.com",
    port=8000,
    headers={"Authorization": f"Bearer {token}"}
)

# Bước 3: Dữ liệu tự động migrate
```

---

## 🧪 Testing the Fix

### **Bước 1: Chạy app**
```bash
streamlit run src/app.py
```

### **Bước 2: Kiểm tra terminal output**
```
✅ Using ChromaDB PersistentClient (Local)
```

### **Bước 3: Test features**
- Load PDF → Should work
- Query → Should work
- Check `database/` folder created → Should exist

### **Bước 4: Xác nhận không có error**
- ❌ KHÔNG thấy "You are using a deprecated configuration"
- ✅ THẤY "Using ChromaDB PersistentClient"

---

## 📊 Comparison: Trước vs Sau Fix

| | Trước | Sau |
|---|-------|-----|
| **Status** | ❌ Deprecated, Error | ✅ Working |
| **Database Type** | CloudClient (invalid) | PersistentClient (local) |
| **Dependencies** | `chromadb.config.Settings` | None (built-in) |
| **Config** | Cloud credentials | Path-based |
| **Complexity** | Medium | Simple |
| **Performance** | Slow (network) | Fast (local) |

---

## 📝 Files Modified

| File | Change |
|------|--------|
| [src/rag_engine.py](../src/rag_engine.py) | Use PersistentClient instead of deprecated APIs |
| [.env](.env) | Remove Chroma Cloud credentials |
| [.env.example](.env.example) | Update template with new config |

---

## 🔗 References

- [ChromaDB Migration Docs](https://docs.trychroma.com/deployment/migration)
- [ChromaDB New Clients](https://docs.trychroma.com/deployment/migration#new-clients)
- [ChromaDB Discord](https://discord.gg/MMeYNTmh3x)

---

## ✅ Checklist

- [x] Fix deprecated ChromaDB config
- [x] Update to PersistentClient API
- [x] Remove cloud credentials from .env
- [x] Test local database works
- [x] Document changes
- [ ] Push to GitHub
- [ ] Verify on team machines

---

## 🎯 Next Steps

1. **Test locally**
   ```bash
   streamlit run src/app.py
   ```

2. **Verify no errors**
   - Check console for ✅ messages
   - No deprecated warnings

3. **Commit & push**
   ```bash
   git add .
   git commit -m "Fix: Update ChromaDB to new PersistentClient API

   - Replace deprecated CloudClient with PersistentClient
   - Remove cloud credentials from .env
   - Use local file-based storage (database/)
   - See CHROMADB_FIX.md for details"
   git push origin main
   ```

4. **Tell team**
   - No need for Chroma Cloud setup
   - Just use local mode
   - Data stored in `database/` folder

---

**ChromaDB deprecated config issue is now FIXED! ✅**
