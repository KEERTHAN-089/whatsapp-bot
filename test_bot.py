import requests

def test_message(message, sender):
    """Send a test message to the bot and print the response."""
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

if __name__ == "__main__":
    print("Testing WhatsApp Catering Bot")
    print("=" * 50)
    
    # Test index endpoint
    index_response = requests.get("http://localhost:5000/")
    print(f"Index response: {index_response.text}")
    print("-" * 50)
    
    # Test admin setting worker count
    test_message("SET 3", "whatsapp:+919353692621")
    
    # Test workers responding "Yes"
    test_message("Yes", "whatsapp:+1234567890")
    test_message("Yes", "whatsapp:+1987654321")
    test_message("Yes", "whatsapp:+1555555555")  # Third worker
    
    # Test worker limit reached
    test_message("Yes", "whatsapp:+1111111111")  # Should get "Sorry, full"
    
    # Test duplicate worker
    test_message("Yes", "whatsapp:+1234567890")  # Already selected
    
    print("Testing complete!")
