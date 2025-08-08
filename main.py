from app import app, logger

if __name__ == '__main__':
    logger.info("Starting WhatsApp Catering Bot from main.py...")
    app.run(debug=True, host='0.0.0.0', port=5000)
