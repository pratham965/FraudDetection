import mysql.connector
import os
from dotenv import load_dotenv
import fastapi
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

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
    transaction_id: str
    transaction_date: str
    transaction_amount: float
    transaction_channel: Optional[str] = None
    transaction_payment_mode: Optional[str] = None
    payment_gateway_bank: Optional[str] = None
    payer_email: Optional[str] = None
    payer_mobile: Optional[str] = None
    payer_card_brand: Optional[str] = None
    payer_ip: Optional[str] = None
    payer_browser: Optional[str] = None
    payee_id: Optional[str] = None

def check_transaction(transaction: dict):
    rules = fetch_rules()
    is_fraud = False
    fraud_reasons = []
    transaction_id = transaction.get("transaction_id")
    
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
                fraud_reasons.append(f"High transaction amount (> {threshold})")

        if blocked_ip and transaction.get("payer_ip") == blocked_ip:
            is_fraud = True
            fraud_reasons.append(f"Blocked IP: {blocked_ip}")

        if blocked_browser and transaction.get("payer_browser") == blocked_browser:
            is_fraud = True
            fraud_reasons.append(f"Blocked Browser: {blocked_browser}")

        if blocked_gateway and transaction.get("payment_gateway_bank") == blocked_gateway:
            is_fraud = True
            fraud_reasons.append(f"Blocked Payment Gateway: {blocked_gateway}")

        if blocked_email and transaction.get("payer_email") == blocked_email:
            is_fraud = True
            fraud_reasons.append(f"Blocked Email: {blocked_email}")

    return {"transaction_id": transaction_id, "is_fraud": is_fraud, "fraud_source": "rule", "fraud_reasons": fraud_reasons}

def upload_transaction(transaction: Transaction, result):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO transactions (
        transaction_id_anonymous, transaction_date, transaction_amount, transaction_channel, 
        transaction_payment_mode_anonymous, payment_gateway_bank_anonymous, payer_email_anonymous, payer_mobile_anonymous, 
        payer_browser_anonymous, payee_id, is_fraud, payee_ip_anonymous
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        transaction.transaction_id, transaction.transaction_date, transaction.transaction_amount,
        transaction.transaction_channel, transaction.transaction_payment_mode, transaction.payment_gateway_bank,
        transaction.payer_email, transaction.payer_mobile,transaction.payer_browser, transaction.payee_id, result,None
    )
    cursor.execute(query, values)
    conn.commit()
    conn.close()

@app.post("/detect")
def detect(transaction: Transaction):
    transaction_dict = transaction.dict()
    result = check_transaction(transaction_dict)
    upload_transaction(transaction, result["is_fraud"])
    return result

class BatchTransactionRequest(BaseModel):
    transactions: List[Transaction]

@app.post("/batchdetect")
def batch_detect(request: BatchTransactionRequest):
    results = {}
    for transaction in request.transactions:
        transaction_dict = transaction.dict()
        result = check_transaction(transaction_dict)
        upload_transaction(transaction, result["is_fraud"])
        results[transaction.transaction_id] = {
            "is_fraud": result["is_fraud"],
            "fraud_reason": ", ".join(result["fraud_reasons"])
        }
    return results

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
