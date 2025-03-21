import streamlit as st
import mysql.connector
import pandas as pd

# ---- Streamlit Page Config ----
st.set_page_config(page_title="Fraud Detection Rule Engine", layout="wide")


# ---- MySQL Connection ----
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="bipul2576",
        database="coderror"
    )


# ---- Function to Fetch Rules ----
def fetch_rules():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM fraud_rules WHERE is_active = 1")
    rules = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rules)


# ---- Function to Add a Rule ----
def add_rule(rule_type, value):
    conn = get_db_connection()
    cursor = conn.cursor()

    if rule_type == "Threshold Value":
        cursor.execute(
            """INSERT INTO fraud_rules (rule_type, threshold) 
            VALUES (%s, %s)""", (rule_type, value)
        )
    elif rule_type == "Blocked IP":
        cursor.execute(
            """INSERT INTO fraud_rules (rule_type, blocked_ip) 
            VALUES (%s, %s)""", (rule_type, value)
        )
    elif rule_type == "Blocked Payment Gateway":
        cursor.execute(
            """INSERT INTO fraud_rules (rule_type, blocked_payment_gateway) 
            VALUES (%s, %s)""", (rule_type, value)
        )

    conn.commit()
    conn.close()

def delete_rule(rule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fraud_rules WHERE id = %s", (rule_id,))
    conn.commit()
    conn.close()
# ---- Streamlit UI ----
st.markdown("<h1>Fraud Detection Rule Engine</h1>", unsafe_allow_html=True)

# 📜 Display Existing Rules
st.subheader("Active Fraud Rules")
rules_df = fetch_rules()
st.dataframe(rules_df, height=300)

# ➕ Add New Rule
st.subheader("Manage Rules")
with st.expander("Add New Rule"):
    rule_type = st.selectbox("Rule Type", ["Threshold Value", "Blocked IP", "Blocked Payment Gateway"])

    if rule_type == "Threshold Value":
        value = st.number_input("Enter Maximum Threshold Value", min_value=0.0)
    elif rule_type == "Blocked IP":
        value = st.text_input("Enter IP Address to Block")
    elif rule_type == "Blocked Payment Gateway":
        value = st.text_input("Enter Payment Gateway to Block")

    if st.button("Add Rule"):
        add_rule(rule_type, value)
        st.success("Rule Added Successfully!")
st.subheader("Delete Rule")
with st.expander("Delete Rule"):
    rule_id = st.number_input("Enter Rule ID to Delete", min_value=1, step=1)
    if st.button("Delete Rule"):
        delete_rule(rule_id)
        st.warning("Rule Deleted Successfully!")