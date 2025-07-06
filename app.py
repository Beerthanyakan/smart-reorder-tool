
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
**RU Score (Reorder Urgency)** คือคะแนนที่บอกระดับความเร่งด่วนในการสั่งซื้อสินค้าใหม่ หากสินค้าหมดสต็อก  
- ถ้า **คะแนนสูงมาก** → สินค้าตัวนี้สำคัญ! ถ้าขาดสต็อกจะ **เสียโอกาสกำไร** มาก  
- คำนวณจาก: กำไรเฉลี่ยต่อวัน ÷ จำนวนวันที่คาดว่า stock จะขายได้ (Stock Coverage)
    """)
    category_selection_placeholder = st.empty()

# Centered Run Button
st.markdown("### ")
run_center = st.columns([2, 1, 2])[1]  # center column in 3-part layout
with run_center:
    run_analysis = st.button("▶️ Run Analysis")

if run_analysis and uploaded_file and uploaded_stock:
    sales_df = pd.read_csv(uploaded_file)
    stock_df = pd.read_csv(uploaded_stock)

    stock_df = stock_df.rename(columns={"In stock [I-animal]": "คงเหลือ", "Cost": "ต้นทุนเฉลี่ย/ชิ้น"})
    stock_df["คงเหลือ"] = stock_df["คงเหลือ"].fillna(0)

    sales_df["จำนวนขาย"] = sales_df["Items sold"] - sales_df["Items refunded"]
    sales_df["ต้นทุนเฉลี่ย/ชิ้น"] = sales_df["Cost of goods"] / sales_df["จำนวนขาย"]
    sales_df["ยอดขายรวม"] = sales_df["Net sales"]

    grouped_sales = sales_df.groupby("SKU").agg(
        total_sales=("จำนวนขาย", "sum"),
        total_revenue=("ยอดขายรวม", "sum"),
        avg_cost_per_unit=("ต้นทุนเฉลี่ย/ชิ้น", "mean")
    ).reset_index()

    merged_df = pd.merge(stock_df, grouped_sales, on="SKU", how="left")
    merged_df["ต้นทุนเฉลี่ย/ชิ้น"] = merged_df["avg_cost_per_unit"].fillna(merged_df["ต้นทุนเฉลี่ย/ชิ้น"])
    merged_df["total_sales"] = merged_df["total_sales"].fillna(0)
    merged_df["total_revenue"] = merged_df["total_revenue"].fillna(0)

    merged_df["total_profit"] = merged_df["total_revenue"] - (merged_df["total_sales"] * merged_df["ต้นทุนเฉลี่ย/ชิ้น"])
    merged_df["avg_profit_per_day"] = merged_df["total_profit"] / stock_days
    merged_df["avg_sales_per_day"] = merged_df["total_sales"] / stock_days

    merged_df["Stock Coverage (Day)"] = merged_df.apply(
        lambda row: row["คงเหลือ"] / row["avg_sales_per_day"] if row["avg_sales_per_day"] > 0 else None,
        axis=1
    )

    def compute_status_and_score(row):
        if row["คงเหลือ"] < 0:
            return "Stock ติดลบ", row["avg_profit_per_day"]
        elif row["คงเหลือ"] == 0 and row["total_sales"] > 0:
            return "หมด!!!", row["avg_profit_per_day"]
        elif row["คงเหลือ"] == 0 and row["total_sales"] == 0:
            return "ไม่มียอดขาย Stock = 0", 0
        elif row["คงเหลือ"] > 0 and row["total_sales"] == 0:
            return "ขายไม่ได้เลยย T_T", 0
        else:
            score = row["avg_profit_per_day"] / row["Stock Coverage (Day)"] if row["Stock Coverage (Day)"] else 0
            return f"{row['Stock Coverage (Day)']:.1f} วัน", score

    merged_df[["สถานะ", "RU Score"]] = merged_df.apply(compute_status_and_score, axis=1, result_type="expand")
    merged_df = merged_df[merged_df["สถานะ"] != "ไม่มียอดขาย Stock = 0"]

    merged_df["ควรสั่งซื้อเพิ่ม (ชิ้น)"] = (merged_df["avg_sales_per_day"] * stock_days - merged_df["คงเหลือ"]).apply(lambda x: max(0, int(np.ceil(x))))
    merged_df["RU Score"] = merged_df["RU Score"].astype(float).round(1)
    merged_df["วันที่ไม่มีของขาย"] = (reorder_days - merged_df["Stock Coverage (Day)"]).apply(lambda x: max(0, int(np.ceil(x))))
    merged_df["Opp. Loss (Baht)"] = (merged_df["avg_profit_per_day"] * merged_df["วันที่ไม่มีของขาย"]).round(2)

    if "Category" in merged_df.columns:
        available_categories = merged_df["Category"].dropna().unique().tolist()
        default_exclude = ["Bird", "Online selling", "แลกแต้ม", "อาบน้ำแมว"]
        default_include = [cat for cat in available_categories if cat not in default_exclude]
        selected_categories = category_selection_placeholder.multiselect("📂 เลือก Category ที่จะแสดง", available_categories, default=default_include)
        merged_df = merged_df[merged_df["Category"].isin(selected_categories)]

    st.divider()
    st.subheader("📂 สรุปความเสี่ยงรวมตามหมวดสินค้า (Category Summary)")

    if "Category" in merged_df.columns:
        summary = merged_df.groupby("Category").agg(Total_RU_Score=("RU Score", "sum")).reset_index()
        st.dataframe(summary)

        category_list = summary.sort_values("Total_RU_Score", ascending=False)["Category"]
        for cat in category_list:
            cat_df = merged_df[merged_df["Category"] == cat].copy()
            cat_df = cat_df.sort_values(by="RU Score", ascending=False).reset_index(drop=True)
            cat_df.index += 1
            display_df = cat_df[["Name", "ควรสั่งซื้อเพิ่ม (ชิ้น)", "สถานะ", "RU Score", "Opp. Loss (Baht)"]].copy()
            display_df.insert(0, "No.", display_df.index)
            st.markdown(f"#### 🗂️ {cat} (RU Score = {cat_df['RU Score'].sum():,.2f})")
            st.dataframe(display_df)
