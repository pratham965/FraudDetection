import mysql.connector
import json, os
from dotenv import load_dotenv
import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = fastapi.FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this for security in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- MySQL Connection ----
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DB")
    )

# ---- Fetch Active Rules from Database ----
def fetch_rules():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM fraud_rules WHERE is_active = 1")
    rules = cursor.fetchall()
    conn.close()
    return rules

# ---- Define Transaction Model ----
class Transaction(BaseModel):
    transaction_amount: float
    transaction_date: str
    transaction_time: str
    transaction_channel: str
    transaction_payment_mode_anonymous: str
    payment_gateway_bank_anonymous: str
    payer_browser_anonymous: str
    payer_email_anonymous: str
    payee_ip_anonymous: str
    payer_mobile_anonymous: str
    transaction_id_anonymous: str
    payee_id_anonymous: str

# ---- Apply Rules to a Transaction ----
def check_transaction(transaction: dict):
    rules = fetch_rules()
    is_fraud = False
    fraud_reasons = []
    
    for rule in rules:
        rule_type = rule.get("rule_type", "")
        threshold = rule.get("threshold", None)

        # Fetch additional blocking conditions
        blocked_ip = rule.get("blocked_ip", None)
        blocked_browser = rule.get("blocked_payer_browser", None)
        blocked_gateway = rule.get("blocked_payment_gateway", None)
        blocked_email = rule.get("blocked_email", None)

        # Apply numeric threshold rules
        if rule_type == "Threshold Value" and threshold is not None:
            if transaction.get("transaction_amount", 0) > float(threshold):
                is_fraud = True
                fraud_reasons.append(f"High transaction amount (>{threshold})")

        # Additional direct matching conditions
        if blocked_ip and transaction.get("payee_ip_anonymous") == blocked_ip:
            is_fraud = True
            fraud_reasons.append(f"Blocked IP: {blocked_ip}")

        if blocked_browser and transaction.get("payer_browser_anonymous") == blocked_browser:
            is_fraud = True
            fraud_reasons.append(f"Blocked Browser: {blocked_browser}")

        if blocked_gateway and transaction.get("payment_gateway_bank_anonymous") == blocked_gateway:
            is_fraud = True
            fraud_reasons.append(f"Blocked Payment Gateway: {blocked_gateway}")

        if blocked_email and transaction.get("payer_email_anonymous") == blocked_email:
            is_fraud = True
            fraud_reasons.append(f"Blocked Email: {blocked_email}")

    return {"is_fraud": is_fraud, "fraud_reasons": fraud_reasons}

# ---- Fraud Detection Endpoint ----
@app.post("/detect")
def detect(transaction: Transaction):
    print(transaction)
    transaction_dict = transaction.dict()
    result = check_transaction(transaction_dict)
    return result

# ---- Run FastAPI App ----
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
