import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# --- Password Protection ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Income & Expense Tracker Login")
    password = st.text_input("Enter password", type="password")
    if st.button("Login"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.success("Login successful!")
        else:
            st.error("Incorrect password")
    st.stop()  # stops the rest of the app from running until login

# --- Database connection (Neon) ---
DATABASE_URL = st.secrets["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

# Create table if not exists
with engine.begin() as conn:
    conn.execute(text('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            date DATE,
            type VARCHAR(10),  -- "income" or "expense"
            category VARCHAR(50),
            amount NUMERIC,
            description TEXT
        )
    '''))

# --- Functions ---
def add_transaction(date, ttype, category, amount, description):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO transactions (date, type, category, amount, description) VALUES (:date, :type, :category, :amount, :description)"),
            {"date": date, "type": ttype, "category": category, "amount": amount, "description": description}
        )

def get_transactions():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM transactions ORDER BY date DESC"))
        rows = result.fetchall()
    return pd.DataFrame(rows, columns=["ID", "Date", "Type", "Category", "Amount", "Description"])

def delete_transaction(txn_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM transactions WHERE id=:id"), {"id": txn_id})

# --- Streamlit UI ---
st.set_page_config(page_title="💰 Income & Expense Tracker", layout="wide")
st.title("💰 Income & Expense Tracker")

# Input form
st.header("Add a New Transaction")
with st.form("transaction_form"):
    date = st.date_input("Date", datetime.today())
    ttype = st.radio("Type", ["Income", "Expense"])
    category = st.text_input("Category", "General")
    amount = st.number_input("Amount", min_value=0.0, format="%.2f")
    description = st.text_area("Description")
    submitted = st.form_submit_button("Add Transaction")

    if submitted:
        add_transaction(date.strftime("%Y-%m-%d"), ttype.lower(), category, amount, description)
        st.success(f"{ttype} added!")

# Show transactions
st.header("All Transactions")
df = get_transactions()
st.dataframe(df, use_container_width=True)

# Summary and Balance
if not df.empty:
    st.subheader("Summary")

    income_total = df[df["Type"] == "income"]["Amount"].sum()
    expense_total = df[df["Type"] == "expense"]["Amount"].sum()
    balance = income_total - expense_total

    st.metric("Total Income", f"${income_total:,.2f}")
    st.metric("Total Expenses", f"${expense_total:,.2f}")
    st.metric("Balance", f"${balance:,.2f}")

    # Fix for bar_chart MultiIndex issue
    summary_df = df.groupby(["Type", "Category"])["Amount"].sum().reset_index()
    st.bar_chart(summary_df, x="Category", y="Amount", width="stretch")


# Delete transactions
st.header("Delete Transaction")
if not df.empty:
    txn_id = st.number_input("Transaction ID to delete", min_value=1, step=1)
    if st.button("Delete"):
        delete_transaction(txn_id)
        st.warning(f"Deleted transaction with ID {txn_id}")

