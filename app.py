
import streamlit as st
import pandas as pd

st.title("🧮 Smart Reorder Tool")

st.markdown("### ℹ️ เกี่ยวกับ Reorder Urgency Score")
st.markdown("""
**Reorder Urgency Score** คือคะแนนที่บอกระดับความเร่งด่วนในการสั่งซื้อสินค้าใหม่ หากสินค้าหมดสต็อก  
- ถ้า **คะแนนสูงมาก** → สินค้าตัวนี้สำคัญ! ถ้าขาดสต็อกจะ **เสียโอกาสกำไร** มาก  
- คำนวณจาก:  
**Reorder Urgency Score = กำไรเฉลี่ยต่อวัน ÷ จำนวนวันที่สินค้าจะยังพอขายได้ (Days Coverage)**
""")

uploaded_file = st.file_uploader("📤 Upload Sales CSV file", type=["csv"])
uploaded_stock = st.file_uploader("📤 Upload Inventory CSV (.csv)", type=["csv"])

days = st.number_input("📅 วางแผนล่วงหน้า (วัน)", value=45, min_value=1)

if uploaded_file and uploaded_stock:
    sales_data = pd.read_csv(uploaded_file)
    stock_df = pd.read_csv(uploaded_stock)

    stock_df = stock_df.rename(columns={"In stock [I-animal]": "คงเหลือ", "Cost": "ต้นทุนเฉลี่ย/ชิ้น"})
    stock_df["คงเหลือ"] = stock_df["คงเหลือ"].fillna(0)

    sales_data["จำนวนขาย"] = sales_data["Items sold"] - sales_data["Items refunded"]
    sales_data["ต้นทุนเฉลี่ย/ชิ้น"] = sales_data["Cost of goods"] / sales_data["จำนวนขาย"]
    sales_data["ยอดขายรวม"] = sales_data["Net sales"]

    grouped_sales = sales_data.groupby("SKU").agg(
        total_sales=("จำนวนขาย", "sum"),
        total_revenue=("ยอดขายรวม", "sum"),
        avg_cost_per_unit=("ต้นทุนเฉลี่ย/ชิ้น", "mean")
    ).reset_index()

    merged_df = pd.merge(stock_df, grouped_sales, on="SKU", how="left")
    merged_df["ต้นทุนเฉลี่ย/ชิ้น"] = merged_df["avg_cost_per_unit"].fillna(merged_df["ต้นทุนเฉลี่ย/ชิ้น"])
    merged_df["total_sales"] = merged_df["total_sales"].fillna(0)
    merged_df["total_revenue"] = merged_df["total_revenue"].fillna(0)

    merged_df["total_profit"] = merged_df["total_revenue"] - (merged_df["total_sales"] * merged_df["ต้นทุนเฉลี่ย/ชิ้น"])
    merged_df["avg_profit_per_day"] = merged_df["total_profit"] / days
    merged_df["avg_sales_per_day"] = merged_df["total_sales"] / days

    merged_df["days_coverage"] = merged_df.apply(
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
            score = row["avg_profit_per_day"] / row["days_coverage"] if row["days_coverage"] else 0
            return f"{row['days_coverage']:.1f} วัน", score

    merged_df[["สถานะ", "Reorder_Urgency_Score"]] = merged_df.apply(compute_status_and_score, axis=1, result_type="expand")

    # Filter by selected categories
    if "Category" in merged_df.columns:
        available_categories = merged_df["Category"].dropna().unique().tolist()
        selected_cats = st.multiselect("📂 เลือกหมวดหมู่ที่จะแสดง", available_categories, default=[cat for cat in available_categories if cat.lower() != "promotion"])
        merged_df = merged_df[merged_df["Category"].isin(selected_cats)]

    merged_df = merged_df.sort_values(by="Reorder_Urgency_Score", ascending=False)

    st.subheader("📂 สรุปความเสี่ยงรวมตามหมวดสินค้า (Category Summary)")
    if "Category" in merged_df.columns:
        summary = merged_df.groupby("Category").agg(Total_Reorder_Urgency_Score=("Reorder_Urgency_Score", "sum")).reset_index()
        st.dataframe(summary)

        for cat in summary["Category"]:
            cat_df = merged_df[merged_df["Category"] == cat]
            cat_df_display = cat_df[["Name", "SKU", "สถานะ", "Reorder_Urgency_Score"]]
            total_score = cat_df["Reorder_Urgency_Score"].sum()
            st.markdown(f"#### 🗂️ {cat} (รวม Reorder Urgency Score: {total_score:,.2f})")
            st.dataframe(cat_df_display.reset_index(drop=True))
