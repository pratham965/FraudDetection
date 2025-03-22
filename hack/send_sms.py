import os
import logging
from twilio.rest import Client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")


def send_twilio_message(to_phone_number: str, message: str) -> bool:
    """
    Send an SMS message using Twilio.

    Args:
        to_phone_number (str): The recipient's phone number in E.164 format (e.g., +1234567890)
        message (str): The message content to send

    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    # Check if Twilio credentials are available
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.warning("Twilio credentials are not configured. SMS notification could not be sent.")
        logger.warning(
            "Make sure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables are set.")
        return False

    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Send message
        twilio_message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )

        logger.info(f"Sent message to {to_phone_number}: SID {twilio_message.sid}")
        return True

    except Exception as e:
        logger.error(f"Failed to send SMS: {str(e)}")
        return False