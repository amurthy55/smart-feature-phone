# ================= CONFIG =================
# Copy this file to config.py and fill in your actual values
# DO NOT commit config.py to version control

PORT = "/dev/serial0"
BAUD = "9600"
MODEL = "gpt-4o"
MAX_SMS_LEN = 160
DEBUG = True

# Phone numbers
ADMIN_NUMBER = "+91XXXXXXXXXX"
MASTER = "+91XXXXXXXXXX"
ANU = "+91XXXXXXXXXX"
MUSE = "+91XXXXXXXXXX"
BASKARAN1 = "+91XXXXXXXXXX"
BASKARAN2 = "+91XXXXXXXXXX"

# Telegram group IDs
PPMS_TELE_GROUP_ID = "-100XXXXXXXXXX"
MOTOR_TELE_GROUP_ID = "-100XXXXXXXXXX"

# Telegram bot token (for direct API sends)
TELE_BOT_TOKEN = "YOUR_BOT_TOKEN"

# Google Drive / Google Auth settings
GOOGLE_DRIVE_ID = "YOUR_FOLDER_ID"
GOOGLE_AUTH_MODE = "oauth"  # or "service_account"
GOOGLE_CREDENTIALS_PATH = "client_secret_XXXX.apps.googleusercontent.com.json"
GOOGLE_TOKEN_PATH = "google_token.json"

INSURANCE_DRIVE_POLL_SECONDS = 300

# === DAILY MASTER MESSAGES ===
DAILY_MSG = [
    "Your health is your first investment; protect it daily.",
    "Strong body, sharp mind, stronger business.",
    # Add more quotes here
]

# === MUSE MESSAGES ===
MUSE_MESSAGES = [
    "Message 1",
    "Message 2",
    # Add more messages here
]

# === LOGGING ===
RING_WINDOW_SEC = 15
LOG_BASE = "/var/log/sms_ai"
CONTEXT_HOURS = 24
MAX_CONTEXT_CHARS = 1200
DAILY_TIMES = ["09:45", "12:00", "16:00"]
