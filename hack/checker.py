import mysql.connector
import json

# ---- MySQL Connection ----
def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="bipul2576",
        database="coderror"
    )

# ---- Fetch Active Rules from Database ----
def fetch_rules():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM fraud_rules WHERE is_active = 1")
    rules = cursor.fetchall()
    conn.close()
    return rules

# ---- Apply Rules to a Transaction ----
def check_transaction(transaction):
    rules = fetch_rules()
    is_fraud = False
    fraud_reasons = []

    for rule in rules:
        rule_type = rule.get("rule_type", "")
        threshold = rule.get("threshold", None)

        # Fetching additional blocking conditions safely
        blocked_ip = rule.get("blocked_ip", None)
        blocked_browser = rule.get("blocked_payer_browser", None)
        blocked_gateway = rule.get("blocked_payment_gateway", None)
        blocked_email = rule.get("blocked_email", None)

        # Apply numeric threshold rules
        if rule_type == "amount" and threshold is not None:
            if transaction.get("amount", 0) > float(threshold):
                is_fraud = True
                fraud_reasons.append(f"High transaction amount (>{threshold})")

        if rule_type == "count_last_10min" and threshold is not None:
            if transaction.get("count_last_10min", 0) > float(threshold):
                is_fraud = True
                fraud_reasons.append(f"Too many transactions in short time (> {threshold})")

        # Additional direct matching conditions (if values are not None)
        if blocked_ip and transaction.get("ip_address") == blocked_ip:
            is_fraud = True
            fraud_reasons.append(f"Blocked IP: {blocked_ip}")

        if blocked_browser and transaction.get("browser") == blocked_browser:
            is_fraud = True
            fraud_reasons.append(f"Blocked Browser: {blocked_browser}")

        if blocked_gateway and transaction.get("payment_gateway") == blocked_gateway:
            is_fraud = True
            fraud_reasons.append(f"Blocked Payment Gateway: {blocked_gateway}")

        if blocked_email and transaction.get("email") == blocked_email:
            is_fraud = True
            fraud_reasons.append(f"Blocked Email: {blocked_email}")

    return is_fraud, fraud_reasons

# ---- Example Usage ----
if __name__ == "__main__":
    transaction = {
        "amount": 150000,  # High amount
        "count_last_10min": 6,  # Frequent transactions
        "ip_address": "192.168.2.1",  # Example IP
        "browser": "Chrome",  # Example browser
        "payment_gateway": "XYZPay",  # Example gateway
        "email": "fraud@example.com"  # Example email
    }

    is_fraud, reasons = check_transaction(transaction)

    print("\nTransaction Data:", json.dumps(transaction, indent=4))
    print("Fraud Detected:", is_fraud)
    print("Fraud Reasons:", reasons if reasons else "No fraud detected.")
