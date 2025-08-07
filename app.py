from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client
import logging
import uuid
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twilio credentials - replace with your actual credentials
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'your_account_sid')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'your_auth_token')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', 'whatsapp:+14155238886')  # Default Twilio sandbox number

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Set up scheduler for reminders
scheduler = BackgroundScheduler()
scheduler.start()

# Data storage functions
def save_data():
    """Save the work opportunities data to a JSON file"""
    data = {
        'work_opportunities': work_opportunities,
        'current_work_id': current_work_id
    }
    with open('catering_data.json', 'w') as f:
        json.dump(data, f)
    logger.info("Data saved to file.")

def load_data():
    """Load the work opportunities data from a JSON file"""
    global work_opportunities, current_work_id
    try:
        if os.path.exists('catering_data.json'):
            with open('catering_data.json', 'r') as f:
                data = json.load(f)
                work_opportunities = data.get('work_opportunities', {})
                current_work_id = data.get('current_work_id')
            logger.info("Data loaded from file.")
        else:
            logger.info("No data file found. Starting with empty data.")
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")

# Global variables
admin_number = "whatsapp:+919353692621"  # WhatsApp format with 'whatsapp:' prefix

# Data structure for work opportunities
work_opportunities = {}  # Dictionary to store work details, keyed by work_id
current_work_id = None  # The active work ID that workers are responding to
admin_state = {}  # Store admin state for multi-step operations

# Load data on startup
load_data()

# Function to send reminders
def send_reminder(work_id, message):
    """Send a reminder to all workers for a specific work opportunity"""
    if work_id in work_opportunities:
        work = work_opportunities[work_id]
        workers = work["selected_workers"]
        
        if not workers:
            logger.info(f"No workers to send reminder for {work_id}")
            return
        
        for worker in workers:
            try:
                twilio_client.messages.create(
                    body=f"REMINDER for {work['title']}: {message}",
                    from_=TWILIO_PHONE_NUMBER,
                    to=worker
                )
                logger.info(f"Sent reminder to {worker} for {work['title']}")
            except Exception as e:
                logger.error(f"Error sending reminder to {worker}: {str(e)}")
        
        # Add reminder to work record
        if "reminders" not in work:
            work["reminders"] = []
        
        work["reminders"].append({
            "message": message,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "recipients": len(workers)
        })
        
        # Save data after sending reminders
        save_data()
        
        logger.info(f"Reminder sent to {len(workers)} workers for {work['title']}")
    else:
        logger.error(f"Cannot send reminder - Work ID {work_id} not found")

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    # Declare global variables at the beginning of the function
    global current_work_id
    
    # Get the message and sender's phone number
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    logger.info(f"Received message: '{incoming_msg}' from {sender}")
    
    # Initialize response
    resp = MessagingResponse()
    
    # Admin commands
    if sender == admin_number:
        # Check if admin is in the middle of creating an event or reminder
        if sender in admin_state:
            if admin_state[sender]['action'] == 'creating_event':
                step = admin_state[sender]['step']
                data = admin_state[sender]['data']
                
                if step == 'title':
                    data['title'] = incoming_msg
                    admin_state[sender]['step'] = 'location'
                    resp.message("Great! Now send the location:")
                elif step == 'location':
                    data['location'] = incoming_msg
                    admin_state[sender]['step'] = 'time'
                    resp.message("When is this event? (date and time):")
                elif step == 'time':
                    data['time'] = incoming_msg
                    admin_state[sender]['step'] = 'workers'
                    resp.message("How many workers are needed? (number only):")
                elif step == 'workers':
                    try:
                        data['required_workers'] = int(incoming_msg)
                        admin_state[sender]['step'] = 'payment'
                        resp.message("What is the payment for workers?")
                    except ValueError:
                        resp.message("Please enter a valid number for workers needed.")
                elif step == 'payment':
                    data['payment'] = incoming_msg
                    
                    # Create work ID
                    work_id = str(uuid.uuid4())[:8]  # Short UUID
                    
                    # Store work details
                    work_opportunities[work_id] = {
                        "title": data['title'],
                        "location": data['location'],
                        "time": data['time'],
                        "required_workers": data['required_workers'],
                        "payment": data['payment'],
                        "selected_workers": [],
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Set as current work
                    current_work_id = work_id
                    
                    # Clear admin state
                    del admin_state[sender]
                    
                    resp.message(f"✅ Work opportunity created!\n\nID: {work_id}\nEvent: {data['title']}\nLocation: {data['location']}\nTime: {data['time']}\nWorkers: {data['required_workers']}\nPayment: {data['payment']}\n\nWorkers can now reply 'Yes' to confirm.")
                
                return str(resp)
            
            elif admin_state[sender]['action'] == 'creating_reminder':
                step = admin_state[sender]['step']
                data = admin_state[sender]['data']
                
                if step == 'message':
                    data['message'] = incoming_msg
                    admin_state[sender]['step'] = 'hours'
                    resp.message("How many hours before the event should this reminder be sent?")
                elif step == 'hours':
                    try:
                        hours = int(incoming_msg)
                        if hours <= 0:
                            resp.message("Hours must be a positive number. Please try again:")
                            return str(resp)
                        
                        data['hours'] = hours
                        work_id = data['work_id']
                        
                        # Schedule the reminder
                        work = work_opportunities[work_id]
                        event_time_str = work['time']
                        
                        # Try to parse the event time - this is a simplification
                        # In production, you'd want more robust datetime parsing
                        try:
                            # For now, just schedule it for X hours from now as a demonstration
                            reminder_time = datetime.now() + timedelta(hours=hours)
                            
                            # Schedule the reminder
                            scheduler.add_job(
                                send_reminder,
                                'date',
                                run_date=reminder_time,
                                args=[work_id, data['message']]
                            )
                            
                            # Record the scheduled reminder
                            if "scheduled_reminders" not in work:
                                work["scheduled_reminders"] = []
                            
                            work["scheduled_reminders"].append({
                                "message": data['message'],
                                "hours_before": hours,
                                "scheduled_for": reminder_time.strftime("%Y-%m-%d %H:%M:%S")
                            })
                            
                            # Clear admin state
                            del admin_state[sender]
                            
                            resp.message(f"✅ Reminder set for {work['title']}!\n\nMessage: {data['message']}\nWill be sent {hours} hours before the event\nScheduled for: {reminder_time.strftime('%Y-%m-%d %H:%M')}")
                            
                        except Exception as e:
                            logger.error(f"Error scheduling reminder: {str(e)}")
                            resp.message(f"Could not schedule reminder. Please try again later.")
                            del admin_state[sender]
                    except ValueError:
                        resp.message("Please enter a valid number for hours.")
                
                return str(resp)
        
        # CREATE command - Start the interactive creation process
        elif incoming_msg.lower() == "create":
            admin_state[sender] = {
                'action': 'creating_event',
                'step': 'title',
                'data': {}
            }
            resp.message("Let's create a new work opportunity.\n\nWhat's the event name?")
        
        # Original CREATE command - Format: CREATE Event Name, Location, Time, Workers Needed, Payment
        elif incoming_msg.lower().startswith("create "):
            try:
                # Remove the "CREATE " prefix
                work_details = incoming_msg[7:].split(",")
                if len(work_details) < 5:
                    resp.message("Invalid format. Use: CREATE Event Name, Location, Time, Workers Needed, Payment")
                    return str(resp)
                
                title = work_details[0].strip()
                location = work_details[1].strip()
                time = work_details[2].strip()
                try:
                    required_workers = int(work_details[3].strip())
                except ValueError:
                    resp.message("Workers needed must be a number.")
                    return str(resp)
                payment = work_details[4].strip()
                
                # Create work ID
                work_id = str(uuid.uuid4())[:8]  # Short UUID
                
                # Store work details
                work_opportunities[work_id] = {
                    "title": title,
                    "location": location,
                    "time": time,
                    "required_workers": required_workers,
                    "payment": payment,
                    "selected_workers": [],
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Set as current work
                current_work_id = work_id
                
                resp.message(f"✅ Work opportunity created!\n\nID: {work_id}\nEvent: {title}\nLocation: {location}\nTime: {time}\nWorkers: {required_workers}\nPayment: {payment}\n\nWorkers can now reply 'Yes' to confirm.")
            except Exception as e:
                logger.error(f"Error creating work: {str(e)}")
                resp.message("Error creating work opportunity. Please check format and try again.")
        
        # LIST command - List all work opportunities
        elif incoming_msg.lower() == "list":
            if not work_opportunities:
                resp.message("No work opportunities available.")
            else:
                work_list = "📋 Available Work Opportunities:\n\n"
                for work_id, work in work_opportunities.items():
                    work_list += f"ID: {work_id}\nEvent: {work['title']}\nTime: {work['time']}\nWorkers: {len(work['selected_workers'])}/{work['required_workers']}\n\n"
                resp.message(work_list)
        
        # SELECT command - Set current work ID for incoming responses
        elif incoming_msg.lower().startswith("select "):
            work_id = incoming_msg[7:].strip()
            if work_id in work_opportunities:
                current_work_id = work_id
                work = work_opportunities[work_id]
                resp.message(f"Selected work ID: {work_id}\nEvent: {work['title']}\nResponses will now be assigned to this event.")
            else:
                resp.message(f"Work ID {work_id} not found. Use LIST to see available work opportunities.")
        
        # STATUS command - Check status of a specific work or all work
        elif incoming_msg.lower() == "status" or incoming_msg.lower() == "count":
            if current_work_id and current_work_id in work_opportunities:
                work = work_opportunities[current_work_id]
                if not work["selected_workers"]:
                    resp.message(f"No workers selected yet for {work['title']}. Need {work['required_workers']} workers.")
                else:
                    worker_numbers = "\n".join([num.replace("whatsapp:", "") for num in work["selected_workers"]])
                    resp.message(f"Current status for {work['title']}: {len(work['selected_workers'])}/{work['required_workers']} workers selected.\n\nSelected workers:\n{worker_numbers}")
            else:
                resp.message("No active work selected. Use SELECT command to choose a work ID.")
        
        # DELETE command - Remove a work opportunity
        elif incoming_msg.lower().startswith("delete "):
            work_id = incoming_msg[7:].strip()
            if work_id in work_opportunities:
                del work_opportunities[work_id]
                if current_work_id == work_id:
                    current_work_id = None
                resp.message(f"Work opportunity {work_id} deleted.")
            else:
                resp.message(f"Work ID {work_id} not found.")
        
        # CANCEL command - Cancel current operation
        elif incoming_msg.lower() == "cancel":
            if sender in admin_state:
                del admin_state[sender]
                resp.message("Operation cancelled.")
            else:
                resp.message("No active operation to cancel.")
        
        # REMIND command - Start interactive reminder creation
        elif incoming_msg.lower() == "remind":
            if not current_work_id or current_work_id not in work_opportunities:
                resp.message("No active work selected. Use SELECT command to choose a work ID first.")
            else:
                work = work_opportunities[current_work_id]
                admin_state[sender] = {
                    'action': 'creating_reminder',
                    'step': 'message',
                    'data': {
                        'work_id': current_work_id
                    }
                }
                resp.message(f"Setting a reminder for '{work['title']}'.\n\nWhat message should be sent to the workers?")
        
        # REMIND with arguments: REMIND work_id, message, hours
        elif incoming_msg.lower().startswith("remind "):
            try:
                # Remove the "REMIND " prefix
                reminder_details = incoming_msg[7:].split(",")
                if len(reminder_details) < 3:
                    resp.message("Invalid format. Use: REMIND work_id, message, hours")
                    return str(resp)
                
                work_id = reminder_details[0].strip()
                message = reminder_details[1].strip()
                
                try:
                    hours = int(reminder_details[2].strip())
                    if hours <= 0:
                        resp.message("Hours must be a positive number.")
                        return str(resp)
                except ValueError:
                    resp.message("Hours must be a number.")
                    return str(resp)
                
                if work_id not in work_opportunities:
                    resp.message(f"Work ID {work_id} not found. Use LIST to see available work opportunities.")
                    return str(resp)
                
                work = work_opportunities[work_id]
                
                # Schedule the reminder (same logic as in the interactive method)
                reminder_time = datetime.now() + timedelta(hours=hours)
                
                # Schedule the reminder
                scheduler.add_job(
                    send_reminder,
                    'date',
                    run_date=reminder_time,
                    args=[work_id, message]
                )
                
                # Record the scheduled reminder
                if "scheduled_reminders" not in work:
                    work["scheduled_reminders"] = []
                
                work["scheduled_reminders"].append({
                    "message": message,
                    "hours_before": hours,
                    "scheduled_for": reminder_time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                resp.message(f"✅ Reminder set for {work['title']}!\n\nMessage: {message}\nWill be sent {hours} hours before the event\nScheduled for: {reminder_time.strftime('%Y-%m-%d %H:%M')}")
                
            except Exception as e:
                logger.error(f"Error setting reminder: {str(e)}")
                resp.message("Error setting reminder. Please check format and try again.")
        
        # HELP command - Show available commands
        elif incoming_msg.lower() == "help":
            help_text = "📱 Admin Commands:\n\n"
            help_text += "CREATE - Start interactive work creation\n\n"
            help_text += "CREATE Event Name, Location, Time, Workers Needed, Payment - Create new work in one step\n\n"
            help_text += "LIST - Show all work opportunities\n\n"
            help_text += "SELECT work_id - Set active work for responses\n\n"
            help_text += "STATUS - Check current workers for active work\n\n"
            help_text += "DELETE work_id - Remove a work opportunity\n\n"
            help_text += "CANCEL - Cancel current operation\n\n"
            help_text += "REMIND - Start setting a reminder for workers\n\n"
            help_text += "REMIND work_id, message, hours - Set a reminder in one step\n\n"
            help_text += "HELP - Show this help message"
            resp.message(help_text)
        
        # Unknown admin command
        else:
            resp.message("Unknown admin command. Send HELP to see available commands.")
    
    # Worker responses
    else:
        # Check if the message is "Yes" (case-insensitive)
        if incoming_msg.lower() == "yes":
            # Check if there's an active work opportunity
            if not current_work_id or current_work_id not in work_opportunities:
                resp.message("Sorry, there's no active work opportunity to respond to.")
                return str(resp)
            
            work = work_opportunities[current_work_id]
            
            # Check if the sender is already selected
            if sender in work["selected_workers"]:
                resp.message(f"You are already selected for {work['title']}.")
            # Check if we've reached the limit
            elif len(work["selected_workers"]) >= work["required_workers"]:
                resp.message(f"Sorry, {work['title']} is full.")
            else:
                work["selected_workers"].append(sender)
                resp.message(f"You have been selected for {work['title']}!\n\nLocation: {work['location']}\nTime: {work['time']}\nPayment: {work['payment']}\n\nYou are worker #{len(work['selected_workers'])} of {work['required_workers']}.")
                
                # Notify admin of new selection
                # Note: In a production app, you'd use the Twilio client to send this
                logger.info(f"New worker {sender} selected for {work['title']}. {len(work['selected_workers'])}/{work['required_workers']} filled.")
        
        # Worker requesting info
        elif incoming_msg.lower() == "info":
            if current_work_id and current_work_id in work_opportunities:
                work = work_opportunities[current_work_id]
                resp.message(f"📋 Current opportunity:\n\nEvent: {work['title']}\nLocation: {work['location']}\nTime: {work['time']}\nPayment: {work['payment']}\nPositions: {len(work['selected_workers'])}/{work['required_workers']} filled\n\nReply 'Yes' to confirm your availability.")
            else:
                resp.message("No active work opportunity at the moment.")
        else:
            resp.message("Please respond with 'Yes' to confirm your availability or 'Info' for work details.")
    
    # Log the current state after each request
    if current_work_id and current_work_id in work_opportunities:
        work = work_opportunities[current_work_id]
        logger.info(f"Current workers for {work['title']}: {len(work['selected_workers'])}/{work['required_workers']}")
    
    # Save data after every request
    save_data()
    
    return str(resp)

# Add a /backup endpoint to manually trigger a backup
@app.route('/backup', methods=['GET'])
def backup():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f'catering_data_backup_{timestamp}.json'
        
        data = {
            'work_opportunities': work_opportunities,
            'current_work_id': current_work_id,
            'timestamp': timestamp
        }
        
        with open(backup_filename, 'w') as f:
            json.dump(data, f)
        
        return jsonify({
            "status": "success",
            "message": f"Backup created: {backup_filename}"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Backup failed: {str(e)}"
        }), 500

@app.route('/status', methods=['GET'])
def status():
    if current_work_id and current_work_id in work_opportunities:
        work = work_opportunities[current_work_id]
        return jsonify({
            "work_id": current_work_id,
            "title": work["title"],
            "selected_workers": len(work["selected_workers"]),
            "required_workers": work["required_workers"],
            "is_full": len(work["selected_workers"]) >= work["required_workers"]
        })
    return jsonify({
        "error": "No active work selected"
    })

@app.route('/', methods=['GET'])
def index():
    return "WhatsApp Catering Bot is running!"

if __name__ == '__main__':
    app.run(debug=True)
