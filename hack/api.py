import os
import json
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import threading
from send_sms import send_twilio_message


app = FastAPI(title="Fraud Analysis API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path constants
DATA_DIR = "data"
LATEST_FILE = os.path.join(DATA_DIR, "latest_transactions.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "transaction_history.csv")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Flag to indicate new data availability
new_data_available = False
new_data_lock = threading.Lock()


class Transaction(BaseModel):
    Transaction_ID: str
    Payer_ID: str
    Payee_ID: str
    Amount: float
    Transaction_Channel: str
    Transaction_Payment_Mode: str
    Payment_Gateway_Bank: str
    is_fraud_predicted: Optional[bool] = False
    is_fraud_reported: Optional[bool] = False
    Timestamp: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "Transaction_ID": "T12345",
                "Payer_ID": "P98765",
                "Payee_ID": "R54321",
                "Amount": 500.75,
                "Transaction_Channel": "Online",
                "Transaction_Payment_Mode": "Credit Card",
                "Payment_Gateway_Bank": "XYZ Bank",
                "is_fraud_predicted": False,
                "is_fraud_reported": False
            }
        }


def send_fraud_alert(transaction: Transaction):
    """
    Send an SMS alert for a fraudulent transaction.

    This function is called when a transaction is flagged as potentially fraudulent.
    """
    message = (
        f"FRAUD ALERT: Transaction {transaction.Transaction_ID} for ${transaction.Amount:.2f} "
        f"has been flagged as potentially fraudulent. "
        f"Payment method: {transaction.Transaction_Payment_Mode}, "
        f"Channel: {transaction.Transaction_Channel}"
    )

    # Send the SMS alert using Twilio
    # In a real system, you would fetch the phone number from a database
    # based on the Payer_ID
    try:
        # Use a dummy phone number for testing - in production, this would be fetched from a database
        recipient = "+11234567890"  # This should be replaced with the actual recipient's number

        # Send the message
        success = send_twilio_message(recipient, message)

        if success:
            print(f"Fraud alert SMS sent for transaction {transaction.Transaction_ID}")
        else:
            print(f"Failed to send fraud alert SMS for transaction {transaction.Transaction_ID}")

    except Exception as e:
        print(f"Error sending fraud alert: {str(e)}")


def process_transaction(transaction: Transaction):
    """
    Process a new transaction and save it to the data files.

    Also sends fraud alerts if the transaction is predicted to be fraudulent.
    """
    global new_data_available

    # Add timestamp if not provided
    if not transaction.Timestamp:
        transaction.Timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Convert transaction to DataFrame
    transaction_df = pd.DataFrame([transaction.dict()])

    # Save to latest transactions file
    transaction_df.to_csv(LATEST_FILE, index=False)

    # Append to history file
    if os.path.exists(HISTORY_FILE):
        # Read existing history
        history_df = pd.read_csv(HISTORY_FILE)

        # Append new transaction
        updated_history = pd.concat([history_df, transaction_df], ignore_index=True)

        # Save updated history
        updated_history.to_csv(HISTORY_FILE, index=False)
    else:
        # Create new history file
        transaction_df.to_csv(HISTORY_FILE, index=False)

    # Set flag for new data
    with new_data_lock:
        new_data_available = True

    # Send fraud alert if predicted fraud
    if transaction.is_fraud_predicted:
        send_fraud_alert(transaction)


@app.post("/transactions/", status_code=202)
async def add_transaction(background_tasks: BackgroundTasks, transaction: Transaction):
    """
    Add a new transaction to the system.

    This endpoint accepts transaction data and processes it in the background.
    If the transaction is flagged as fraudulent, a notification will be sent.
    """
    # Process transaction in a background task
    background_tasks.add_task(process_transaction, transaction)

    return {"status": "accepted", "message": "Transaction is being processed"}


@app.get("/health/")
async def healthcheck():
    """
    Simple health check endpoint.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/transactions/")
async def get_transactions(limit: int = 100):
    """
    Get the latest transactions.

    This endpoint returns the most recent transactions, up to the specified limit.
    """
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE)
            if len(df) > limit:
                df = df.tail(limit)

            # Convert boolean columns explicitly
            if 'is_fraud_predicted' in df.columns:
                df['is_fraud_predicted'] = df['is_fraud_predicted'].astype(bool)
            if 'is_fraud_reported' in df.columns:
                df['is_fraud_reported'] = df['is_fraud_reported'].astype(bool)

            # Convert DataFrame to list of dictionaries
            transactions = df.to_dict(orient='records')
            return {"transactions": transactions, "count": len(transactions)}
        except Exception as e:
            return {"error": f"Failed to read transactions: {str(e)}"}

    return {"transactions": [], "count": 0}


def has_new_data():
    """
    Check if new transaction data is available.

    Returns:
        bool: True if new data is available, False otherwise
    """
    global new_data_available
    with new_data_lock:
        return new_data_available


def reset_new_data_flag():
    """
    Reset the new data flag.

    This should be called after the new data has been processed.
    """
    global new_data_available
    with new_data_lock:
        new_data_available = False