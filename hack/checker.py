import mysql.connector
import os
from dotenv import load_dotenv
import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = fastapi.FastAPI()
load_dotenv()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DB")
    )


def fetch_rules():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM fraud_rules WHERE is_active = 1")
    rules = cursor.fetchall()
    conn.close()
    return rules

class Transaction(BaseModel):
    transaction_amount: float
    transaction_date: str
    transaction_channel: str
    transaction_payment_mode_anonymous: str
    payment_gateway_bank_anonymous: str
    payer_browser_anonymous: str
    payer_email_anonymous: str
    payee_ip_anonymous: str
    payer_mobile_anonymous: str
    transaction_id_anonymous: str
    payee_id_anonymous: str

def check_transaction(transaction: dict):
    rules = fetch_rules()
    is_fraud = False
    fraud_reasons = []
    
    for rule in rules:
        rule_type = rule.get("rule_type", "")
        threshold = rule.get("threshold", None)
        blocked_ip = rule.get("blocked_ip", None)
        blocked_browser = rule.get("blocked_payer_browser", None)
        blocked_gateway = rule.get("blocked_payment_gateway", None)
        blocked_email = rule.get("blocked_email", None)

        if rule_type == "Threshold Value" and threshold is not None:
            if transaction.get("transaction_amount", 0) > float(threshold):
                is_fraud = True
                fraud_reasons.append(f"High transaction amount (>{threshold})")

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

def upload_transaction(transaction: Transaction,result):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO transactions (
        transaction_amount, transaction_date, transaction_channel, 
        transaction_payment_mode_anonymous, payment_gateway_bank_anonymous, 
        payer_browser_anonymous, payer_email_anonymous, payee_ip_anonymous, 
        payer_mobile_anonymous, transaction_id_anonymous, payee_id_anonymous, is_fraud
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        transaction.transaction_amount, transaction.transaction_date, transaction.transaction_channel,
        transaction.transaction_payment_mode_anonymous, transaction.payment_gateway_bank_anonymous,
        transaction.payer_browser_anonymous, transaction.payer_email_anonymous, transaction.payee_ip_anonymous,
        transaction.payer_mobile_anonymous, transaction.transaction_id_anonymous, transaction.payee_id_anonymous, result
    )
    cursor.execute(query, values)
    conn.commit()
    conn.close()

@app.post("/detect")
def detect(transaction: Transaction):
    transaction_dict = transaction.dict()
    result = check_transaction(transaction_dict)
    upload_transaction(transaction,result["is_fraud"])
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
