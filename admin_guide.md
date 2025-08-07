# WhatsApp Catering Bot - Admin Command Guide

As the admin (phone number: +919353692621), you can control the bot by sending these commands via WhatsApp:

## Basic Commands

- `HELP` - Shows all available commands
- `STATUS` or `COUNT` - Shows how many workers are selected for the current work opportunity
- `LIST` - Shows all work opportunities you've created

## Creating Work Opportunities

### Method 1: Interactive Creation (Recommended)
1. Send: `CREATE`
2. Bot will ask you for each piece of information one by one:
   - Event name
   - Location
   - Date and time
   - Number of workers needed
   - Payment details

### Method 2: One-Step Creation
Send everything in one message with this format:
```
CREATE Event Name, Location, Time, Workers Needed, Payment
```

Example:
```
CREATE Wedding Reception, Grand Hotel Bangalore, June 15 at 6PM, 8, Rs.800 per person
```

## Managing Work Opportunities

- `SELECT 12345678` - Switch to a specific work opportunity (use the ID from LIST command)
- `DELETE 12345678` - Remove a work opportunity
- `CANCEL` - Cancel any ongoing operation

## Setting Reminders

- `REMIND` - Start interactive reminder creation for the current work opportunity
- `REMIND 12345678, Your reminder message, hours` - Set a reminder for a specific work opportunity
  
Example:
```
REMIND abc123de, Don't forget to bring your uniform tomorrow, 24
```

This will send "Don't forget to bring your uniform tomorrow" to all selected workers 24 hours before the event.

## Example Workflow

1. Send `CREATE` to start creating a new event
2. Follow the prompts to provide details
3. After creation, workers can respond with "Yes" 
4. Check progress with `STATUS`
5. Create another event with `CREATE` if needed
6. Use `LIST` to see all events
7. Use `SELECT` to switch between events

Remember that your phone (+919353692621) is the only one authorized as admin.
