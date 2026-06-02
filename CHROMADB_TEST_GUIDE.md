# ✅ Quick Test Guide - ChromaDB Fix

**Date:** June 2, 2026  
**Issue Fixed:** Deprecated ChromaDB configuration  
**Solution:** Migrated to PersistentClient (Local mode)

---

## 🚀 Quick Start (5 mins)

### **Step 1: Clean Up Old Cache**
```bash
# Delete old database (fresh start recommended)
rmdir /s database
# or (macOS/Linux)
rm -rf database
```

### **Step 2: Run App**
```bash
cd d:\DH_GTVT_HCM\Agent_Law
streamlit run src/app.py
```

### **Step 3: Check Terminal Output**

**✅ EXPECTED (Should see):**
```
✅ Using ChromaDB PersistentClient (Local)
```

**❌ SHOULD NOT SEE:**
```
❌ You are using a deprecated configuration of Chroma.
```

---

## 🧪 Test Scenarios

### **Scenario 1: Load PDF & Index**

1. Place `sample.pdf` in `data/` folder
2. Click **"🔄 Tải Dữ Liệu Mới"** button
3. Wait for indexing...
4. Check console for:
   ```
   ✅ Using ChromaDB PersistentClient (Local)
   ✅ Đã tải X chunks vào ChromaDB
   ```
5. Verify `database/` folder created:
   ```
   database/
   ├── index/
   ├── chroma-collections.parquet
   └── ...
   ```

---

### **Scenario 2: Query**

1. After data loaded, enter question:
   ```
   Quyền lao động của người lao động là gì?
   ```
2. Click **"🔎 Tra Cứu"**
3. Check for:
   - ✅ Response appears within 10 seconds
   - ✅ No deprecated warnings in console
   - ✅ Sources cited at bottom

---

### **Scenario 3: Adjust Parameters**

1. Move `top_k` slider (1-10)
2. Enter new query
3. Should use new `top_k` value
4. Check console for normal operation

---

## 🔍 Troubleshooting

### **Issue 1: Still seeing deprecated warning**

**Solution:**
```bash
# Make sure venv is activated
venv\Scripts\activate

# Reinstall chromadb
pip install --upgrade chromadb

# Clean cache
pip cache purge

# Run again
streamlit run src/app.py
```

---

### **Issue 2: database/ folder not created**

**Solution:**
```bash
# Manually create
mkdir database

# Run app again
streamlit run src/app.py

# Should auto-create on first index
```

---

### **Issue 3: Error "collection already exists"**

**Solution:**
```bash
# This is normal - means data persisted
# Just run query - should work fine

# Or to reset:
rmdir /s database
streamlit run src/app.py
```

---

## 📊 Before & After Comparison

### **Before Fix:**
```
❌ ERROR: You are using a deprecated configuration of Chroma
❌ CloudClient not working
❌ Can't load/query data
```

### **After Fix:**
```
✅ Using ChromaDB PersistentClient (Local)
✅ Data loads successfully
✅ Queries work normally
✅ database/ created automatically
```

---

## 📁 Expected File Structure After Test

```
Agent_Law/
├── database/                 # AUTO-CREATED ✅
│   ├── index/
│   ├── chroma-collections.parquet
│   └── chroma.sqlite3
├── data/
│   └── sample.pdf           # Your test PDF
├── src/
│   ├── app.py
│   ├── data_loader.py
│   └── rag_engine.py
├── .env                      # Updated ✅
└── .env.example              # Updated ✅
```

---

## ✅ Verification Checklist

After running test, verify:

- [ ] App starts without deprecated errors
- [ ] Console shows "Using ChromaDB PersistentClient"
- [ ] PDF loads and chunks successfully
- [ ] Queries return results
- [ ] `database/` folder created
- [ ] top_k slider works
- [ ] Query history displays
- [ ] No warnings in console

---

## 🎯 Success Criteria

✅ **Test PASSED if:**
- No deprecated ChromaDB warnings
- Data loads without errors
- Queries return responses
- Local database working

❌ **Test FAILED if:**
- Still seeing deprecated warnings
- Data fails to load
- Queries error out
- database folder issues

---

## 📞 If Issues Persist

1. Check `.env` has correct `DATABASE_PATH=database`
2. Verify ChromaDB version: `pip show chromadb`
3. Check Python version: `python --version` (should be 3.9+)
4. Try: `pip install --upgrade chromadb`
5. Check GitHub issues: https://github.com/chroma-core/chroma/issues

---

## 🎓 Learning Points

**What Changed:**
- Old: `chromadb.Client(Settings(...))` ❌ Deprecated
- New: `chromadb.PersistentClient(path="...")` ✅ Recommended

**Why:**
- ChromaDB simplified API
- Removed complex Settings object
- Direct path-based initialization
- Better for local development

**Future:**
- If scaling to multiple servers → Use HttpClient
- Current setup good for MVP & dev

---

**Test complete! Ready for team review.** ✅
