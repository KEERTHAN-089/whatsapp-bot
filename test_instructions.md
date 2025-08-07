# Testing the WhatsApp Catering Bot

## Local Testing (Without Twilio)

### Using cURL
You can simulate Twilio requests using cURL:

```bash
curl -X POST http://localhost:5000/whatsapp \
  -d "Body=Yes" \
  -d "From=whatsapp:+1234567890" \
  --header "Content-Type: application/x-www-form-urlencoded"
```

For admin commands:
```bash
curl -X POST http://localhost:5000/whatsapp \
  -d "Body=SET 5" \
  -d "From=whatsapp:+919353692621" \
  --header "Content-Type: application/x-www-form-urlencoded"
```

### Using a Test Script
Create a simple test script (`test_bot.py`):

```python
import requests

def test_message(message, sender):
    url = "http://localhost:5000/whatsapp"
    data = {
        "Body": message,
        "From": sender
    }
    response = requests.post(url, data=data)
    print(f"Message: {message}")
    print(f"Sender: {sender}")
    print(f"Response: {response.text}")
    print("-" * 50)

# Test worker responding "Yes"
test_message("Yes", "whatsapp:+1234567890")

# Test admin setting worker count
test_message("SET 3", "whatsapp:+919353692621")

# Test multiple workers responding to see limit behavior
test_message("Yes", "whatsapp:+1987654321")
test_message("Yes", "whatsapp:+1555555555")
test_message("Yes", "whatsapp:+1111111111")  # Should get "Sorry, full"
```

## Testing with Actual Twilio Service

1. **Deploy your app** - Use Render or ngrok to make your app publicly accessible

2. **Configure Twilio webhook** - Point your Twilio WhatsApp webhook to your deployed URL

3. **Test various scenarios**:
   - Send "Yes" from different WhatsApp numbers
   - Send "SET N" from your admin number
   - Send multiple "Yes" responses to test the limit
   - Send "Yes" from a number that's already been selected

4. **Check logs**:
   - Monitor your Flask app logs
   - Check Twilio console logs for any delivery issues

## Automated Testing (Optional)

Create a more comprehensive test suite with pytest:

```python
# test_app.py
import pytest
from app import app as flask_app
import json

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_index(client):
    response = client.get('/')
    assert b"WhatsApp Catering Bot is running!" in response.data

def test_worker_selection(client):
    # Reset state first by sending admin command
    client.post('/whatsapp', data={
        "Body": "SET 3",
        "From": "whatsapp:+919353692621"
    })
    
    # First worker
    response = client.post('/whatsapp', data={
        "Body": "Yes",
        "From": "whatsapp:+1111111111"
    })
    assert b"You have been selected! You are worker #1 of 3" in response.data
    
    # Second worker
    response = client.post('/whatsapp', data={
        "Body": "Yes",
        "From": "whatsapp:+2222222222"
    })
    assert b"You have been selected! You are worker #2 of 3" in response.data
    
    # Duplicate worker
    response = client.post('/whatsapp', data={
        "Body": "Yes",
        "From": "whatsapp:+1111111111"
    })
    assert b"You are already selected for this event" in response.data
    
    # Third worker
    response = client.post('/whatsapp', data={
        "Body": "Yes",
        "From": "whatsapp:+3333333333"
    })
    assert b"You have been selected! You are worker #3 of 3" in response.data
    
    # Fourth worker (should be rejected)
    response = client.post('/whatsapp', data={
        "Body": "Yes",
        "From": "whatsapp:+4444444444"
    })
    assert b"Sorry, full" in response.data
```

Run with: `pytest test_app.py -v`
