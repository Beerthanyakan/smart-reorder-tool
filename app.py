
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("🧮 Smart Reorder Tool")

# === LAYOUT: LEFT / RIGHT ===
left_col, right_col = st.columns([1, 1])

with left_col:
    uploaded_file = st.file_uploader("📤 Upload \"Sales by item\" file (.CSV)", type=["csv"])
    uploaded_stock = st.file_uploader("📤 Upload \"Inventory\" File (.CSV)", type=["csv"])
    stock_days = st.number_input("📦 Stock Coverage (Day)", value=45, min_value=1)
    reorder_days = st.number_input("🔁 สั่งของอีกครั้งในอีกกี่วัน", value=7, min_value=1)

with right_col:
    st.markdown("### ℹ️ RU Score (Reorder Urgency)")
    st.markdown("""
คะแนนที่บอกระดับความเร่งด่วนในการสั่งซื้อสินค้าใหม่ หากสินค้าหมดสต็อก  
- ถ้า **คะแนนสูงมาก** → สินค้าตัวนี้สำคัญ! ถ้าขาดสต็อกจะ **เสียโอกาสกำไร** มาก
    """)
    category_selection_placeholder = st.empty()

# Centered Run Button
st.markdown("### ")
run_center = st.columns([2, 1, 2])[1]
with run_center:
    run_analysis = st.button("▶️ Run Analysis")

# (rest of code unchanged)
