from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
selected_workers = []  # List to store selected phone numbers
required_workers = 10  # Default value for N
admin_number = "whatsapp:+919353692621"  # WhatsApp format with 'whatsapp:' prefix

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    # Get the message and sender's phone number
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    logger.info(f"Received message: '{incoming_msg}' from {sender}")
    
    # Initialize response
    resp = MessagingResponse()
    
    # Check if message is from admin to update required workers
    if sender == admin_number and incoming_msg.lower().startswith("set "):
        global required_workers, selected_workers
        try:
            new_limit = int(incoming_msg.split(" ")[1])
            required_workers = new_limit
            selected_workers = []  # Reset selected workers
            resp.message(f"Required workers set to {required_workers}. Selection list reset.")
            logger.info(f"Admin updated required workers to {required_workers}")
        except (IndexError, ValueError):
            resp.message("Invalid format. Use 'SET N' where N is a number.")
    
    # Check if the message is "Yes" (case-insensitive)
    elif incoming_msg.lower() == "yes":
        # Check if the sender is already selected
        if sender in selected_workers:
            resp.message("You are already selected for this event.")
        # Check if we've reached the limit
        elif len(selected_workers) >= required_workers:
            resp.message("Sorry, full.")
        else:
            selected_workers.append(sender)
            resp.message(f"You have been selected! You are worker #{len(selected_workers)} of {required_workers}.")
    else:
        resp.message("Please respond with 'Yes' to confirm your availability.")
    
    return str(resp)

@app.route('/', methods=['GET'])
def index():
    return "WhatsApp Catering Bot is running!"

if __name__ == '__main__':
    app.run(debug=True)
