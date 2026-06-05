"""
Quick Start Guide - Hướng Dẫn Nhanh Bắt Đầu

Chạy các lệnh này lần lượt để setup và chạy ứng dụng
"""

# 1. Tạo Virtual Environment
python -m venv venv

# 2. Activate Virtual Environment
# Trên Windows:
venv\Scripts\activate

# Trên macOS/Linux:
# source venv/bin/activate

# 3. Cài đặt Dependencies
pip install -r requirements.txt

# 4. Cấu hình API Key
# - Copy .env.example thành .env
# - Mở .env và paste GEMINI_API_KEY của bạn
# - Lấy API Key tại: https://makersuite.google.com/app/apikey

# 5. Đặt PDF vào thư mục data/
# Ví dụ:
# - data/Bộ_luật_Lao_động.pdf
# - data/Luật_Giao_dịch_Điện_tử.pdf

# 6. Chạy Ứng Dụng
python -m streamlit run app.py

# Ứng dụng sẽ mở tại http://localhost:8501

# ===== TROUBLESHOOTING =====

# Nếu lỗi "ModuleNotFoundError: No module named 'langchain'":
# - Chắc chắn virtual environment được activate
# - Chạy: pip install -r requirements.txt

# Nếu lỗi "GEMINI_API_KEY not found":
# - Tạo file .env
# - Thêm: GEMINI_API_KEY=your_key_here

# Nếu không có PDF nào được tải:
# - Tạo thư mục data/ nếu chưa có
# - Đặt file PDF vào
# - Nhấp "Tải Dữ Liệu Mới" trong app
