import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000/detect"

st.title("💳 Fraud Detection System")

transaction_amount = st.number_input("Transaction Amount", min_value=0.0, step=0.01)
transaction_date = st.date_input("Transaction Date","today")
transaction_channel = st.selectbox("Transaction Channel", ["Online", "In-store", "Mobile"])
transaction_payment_mode_anonymous = st.text_input("Payment Mode")
payment_gateway_bank_anonymous = st.text_input("Payment Gateway/Bank")
payer_browser_anonymous = st.text_input("Payer Browser")
payer_email_anonymous = st.text_input("Payer Email")
payee_ip_anonymous = st.text_input("Payee IP")
payer_mobile_anonymous = st.text_input("Payer Mobile")
transaction_id_anonymous = st.text_input("Transaction ID")
payee_id_anonymous = st.text_input("Payee ID")

if st.button("Check for Fraud"):
    transaction_data = {
        "transaction_amount": transaction_amount,
        "transaction_date": str(transaction_date),
        "transaction_channel": transaction_channel,
        "transaction_payment_mode_anonymous": transaction_payment_mode_anonymous,
        "payment_gateway_bank_anonymous": payment_gateway_bank_anonymous,
        "payer_browser_anonymous": payer_browser_anonymous,
        "payer_email_anonymous": payer_email_anonymous,
        "payee_ip_anonymous": payee_ip_anonymous,
        "payer_mobile_anonymous": payer_mobile_anonymous,
        "transaction_id_anonymous": transaction_id_anonymous,
        "payee_id_anonymous": payee_id_anonymous
    }

    response = requests.post(API_URL, json=transaction_data)

    if response.status_code == 200:
        result = response.json()
        if result["is_fraud"]:
            st.error(f"🚨 Fraud Detected!\nReasons: {', '.join(result['fraud_reasons'])}")
        else:
            st.success("✅ Transaction is NOT Fraudulent!")
    else:
        st.error("❌ Error connecting to API")

