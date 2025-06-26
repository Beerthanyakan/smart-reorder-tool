
import streamlit as st
import pandas as pd

st.title("🧮 Smart Reorder Tool")

uploaded_file = st.file_uploader("📤 Upload Sales Excel file (.xlsx)", type=["xlsx"])
uploaded_stock = st.file_uploader("📤 Upload Inventory CSV (.csv)", type=["csv"])

days = st.number_input("📅 วางแผนล่วงหน้า (วัน)", value=45, min_value=1)

if uploaded_file and uploaded_stock:
    sales_df = pd.read_excel(uploaded_file, sheet_name=None)
    stock_df = pd.read_csv(uploaded_stock)

    sheet_name = [name for name in sales_df if "item-sales" in name][0]
    sales_data = sales_df[sheet_name]

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

    merged_df[["สถานะ", "Loss_Risk_Score"]] = merged_df.apply(compute_status_and_score, axis=1, result_type="expand")
    merged_df = merged_df.sort_values(by="Loss_Risk_Score", ascending=False)

    st.success("📊 ตารางวิเคราะห์ความเสี่ยง (Loss Risk Score):")
    st.dataframe(merged_df)
