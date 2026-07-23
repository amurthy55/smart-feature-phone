# Smart Feature Phone

A Raspberry Pi-based SMS AI Gateway that bridges a GSM feature phone with OpenAI, Telegram, and Google services. It enables SMS-based AI conversations, IoT motor control via missed calls, Telegram alert forwarding, and remote management commands.

## Overview

This project turns a Raspberry Pi with a GSM modem into a smart SMS gateway. Incoming and outgoing SMS are handled through a physical SIM card connected via serial UART. The system can respond to messages using OpenAI's GPT models, relay alerts from Telegram groups, and execute commands sent by authorized users.

## Features

- **SMS-based AI chat:** Any mobile number can text the device and receive AI-generated replies.
- **MASTER commands:** Authorized number can trigger motor control, request IP address, reboot the Pi, and regenerate daily message lists.
- **Missed-call triggers:**
  - **MASTER:** Hangs up and sends a random message to MUSE.
  - **MUSE:** Answers the call, sends a Google Drive link, then disconnects.
  - **BASKARAN1 / BASKARAN2:** Hangs up and sends a "MOTOR ON" message to a Telegram group.
- **Telegram integration:**
  - Polls a Telegram group for BRLog alerts and forwards ERROR / NORMAL status to MASTER via SMS.
  - Sends MOTOR ON messages via Telegram using a Telethon user client.
- **Scheduled messages:** Sends daily messages at configured times.
- **Non-numerical sender forwarding:** Messages from alphanumeric senders (e.g. BSNL) are forwarded to MASTER.
- **Remote management:** MASTER can request the Pi's IP or reboot it via SMS.

## Hardware

- Raspberry Pi (running Raspberry Pi OS / Debian)
- GSM modem / SIM module (e.g. SIM900, connected via `/dev/serial0`)
- UART/serial connection between Pi and modem

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/amurthy55/smart-feature-phone.git
   cd smart-feature-phone
   ```

2. Create a Python virtual environment and install dependencies:
   ```bash
   python3 -m venv sim900-venv
   source sim900-venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy the example configuration file and fill in your actual values:
   ```bash
   cp config.example.py config.py
   nano config.py
   ```

4. Create the log directory:
   ```bash
   sudo mkdir -p /var/log/sms_ai
   sudo chown $(whoami):$(whoami) /var/log/sms_ai
   ```

5. Enable and start the systemd service (optional):
   ```bash
   sudo cp sms-ai-gateway.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now sms-ai-gateway
   ```

## Configuration

All settings are in `config.py`. See `config.example.py` for the structure.

Key settings include:
- `PORT` / `BAUD`: Serial port and baud rate for the modem.
- `MASTER`, `ANU`, `MUSE`, `BASKARAN1`, `BASKARAN2`: Authorized phone numbers.
- `PPMS_TELE_GROUP_ID`: Telegram group ID for BRLog alerts.
- `MOTOR_TELE_GROUP_ID`: Telegram group ID for MOTOR ON messages.
- `MODEL`: OpenAI model name.
- `DAILY_TIMES`: Times for scheduled daily messages.
- `LOG_BASE`: Directory for logs.

## Usage

Send SMS commands from the configured `MASTER` number:

| Command | Action |
|---------|--------|
| `change list` | Regenerate daily quote list |
| `vroom` | Send "MOTOR ON" to Telegram motor group |
| `ip` | Reply with current Pi IP address |
| `reboot` | Reboot the Pi after sending a confirmation |

## Authorized Numbers

- **MASTER:** Full control commands and receives BRLog alert notifications.
- **MUSE:** Receives random messages from MASTER and can request the Google Drive link.
- **ANU:** Receives daily scheduled messages.
- **BASKARAN1 / BASKARAN2:** Missed calls trigger "MOTOR ON" in the configured Telegram group.

## Files

- `sms_ai_gateway.py`: Main daemon that reads modem serial lines, handles SMS/calls, AI, and Telegram polling.
- `poll_telegram_brlog.py`: Telethon-based script to poll a Telegram group for BRLog alerts.
- `send_motor_on.py`: Telethon-based script to send MOTOR ON message to a Telegram group.
- `config.py`: Configuration file (not included in git, see `config.example.py`).

## Logging

Logs are written to `/var/log/sms_ai/`:
- `system.log`: System events, errors, and modem initialization.
- `received.log`: All incoming SMS.
- `sent.log`: All outgoing SMS.

## Security Notes

- `config.py` contains sensitive data (phone numbers, API tokens, Telegram credentials). It is excluded from version control in `.gitignore`.
- The `reboot` command requires the running user to have passwordless `sudo` access to `/sbin/reboot`.
- Telegram API credentials (`API_ID`, `API_HASH`, `PHONE_NUMBER`) are hard-coded in `send_motor_on.py` and `poll_telegram_brlog.py` for the Telethon user client.

## License

MIT
