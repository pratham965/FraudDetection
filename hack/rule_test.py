import streamlit as st
import mysql.connector
import pandas as pd

# ---- Streamlit Page Config ----
st.set_page_config(page_title="Fraud Detection Rule Engine", layout="wide")

# ---- Custom CSS for Dark Mode & UI Enhancements ----
st.markdown(
    """
    <style>

    .stApp {
        background: url("background.png") no-repeat center center fixed;
        background-size: cover;
    }

    /* Centered Title with Padding */
    h1 {
        color: #ff4c4c;  /* Red */
        font-size: 42px;
        font-weight: bold;
        text-align: center;
    }

    /* Subheader Styling */
    h2, h3 {
        color: #4da8da;  /* Light Blue */
        font-weight: bold;
    }

    /* Dataframe Styling */
    .stDataFrame {
        border: 2px solid #4da8da;
        border-radius: 10px;
        padding: 10px;
    }

    /* Style Buttons */
    .stButton>button {
        background-color: #00BFFF;
        color: white;
        border-radius: 8px;
        padding: 10px;
        transition: 0.3s;
        font-weight: bold;
    }

    .stButton>button:hover {
        background-color: #d32f2f;
        transform: scale(1.05);
    }

    /* Style Expander */
    .st-expander {
        border: 2px solid #4da8da !important;
        border-radius: 10px;
        padding: 10px;
        background-color: #1e1e1e;
    }

    /* Text Input Styling */
    .stTextInput>div>div>input {
        border: 2px solid #4da8da;
        border-radius: 5px;
        background-color: #1e1e1e;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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
def add_rule(name, condition, threshold, blocked_ip, blocked_browser, blocked_gateway, blocked_email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO fraud_rules (rule_name, condition_text, threshold, blocked_ip, blocked_payer_browser, blocked_payment_gateway, blocked_email) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (name, condition, threshold, blocked_ip, blocked_browser, blocked_gateway, blocked_email)
    )
    conn.commit()
    conn.close()


# ---- Function to Delete a Rule ----
def delete_rule(rule_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fraud_rules WHERE id = %s", (rule_id,))
    conn.commit()
    conn.close()


# ---- Streamlit UI ----
st.markdown("<h1>Fraud Detection Rule Engine</h1>", unsafe_allow_html=True)

# Layout with Columns
col1, col2 = st.columns([2, 1])

# 📜 Display Existing Rules
with col1:
    st.subheader("Active Fraud Rules")
    rules_df = fetch_rules()

    # Add Search Bar
    search_text = st.text_input("Search Rules by Name", "")
    if search_text:
        rules_df = rules_df[rules_df["rule_name"].str.contains(search_text, case=False, na=False)]

    st.dataframe(rules_df, height=300)

# ➕ Add New Rule
with col2:
    st.subheader("Manage Rules")
    with st.expander("Add New Rule"):
        rule_name = st.text_input("Rule Name")
        condition = st.text_area("Condition (e.g., amount > ?)")
        threshold = st.number_input("Threshold Value", min_value=0.0)
        blocked_ip = st.text_input("Blocked IP Address")
        blocked_browser = st.text_input("Blocked Payer Browser")
        blocked_gateway = st.text_input("Blocked Payment Gateway")
        blocked_email = st.text_input("Blocked Email Address")

        if st.button("Add Rule"):
            add_rule(rule_name, condition, threshold, blocked_ip, blocked_browser, blocked_gateway, blocked_email)
            st.success("Rule Added Successfully!")

# ❌ Delete Rule Section
st.subheader("Manage Rules")
with st.expander("Delete Rule"):
    rule_id = st.number_input("Enter Rule ID to Delete", min_value=1, step=1)
    if st.button("Delete Rule"):
        delete_rule(rule_id)
        st.warning("Rule Deleted Successfully!")
