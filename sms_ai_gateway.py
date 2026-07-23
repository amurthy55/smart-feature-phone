# vetrivel2-pi@raspberrypi:~ $ cat sms_ai_gateway.py
import serial
import time
import re
import os
import requests
import random
import importlib
import subprocess
import sys
import json
from datetime import datetime, timedelta
from openai import OpenAI
import config

last_telegram_check = 0

RECEIVED_LOG = f"{config.LOG_BASE}/received.log"
SENT_LOG = f"{config.LOG_BASE}/sent.log"
SYSTEM_LOG = f"{config.LOG_BASE}/system.log"
BRLOG_ERROR_FLAG = f"{config.LOG_BASE}/brlog_error_flag.txt"

client = OpenAI()
scheduled_jobs = []

# === LIST REGENERATION PROMPTS ===
DAILY_MSG_PROMPT = '''
give me a list of inspirational quotes, 50 of them, themed health and business development. Output ONLY a valid Python list of strings, each item in the list to be concise and sms friendly. Example format: ["quote1", "quote2", "quote3"]
'''

# === DAILY SCHEDULE TRACKER ===
last_daily_sent = {}

# ---------- LOGGING ----------
def log(*args):
    if config.DEBUG:
        print(*args, flush=True)

def log_file(path, line):
    os.makedirs(config.LOG_BASE, exist_ok=True)
    with open(path, "a") as f:
        f.write(line + "\n")

def log_system(msg):
    log_file(SYSTEM_LOG, f"{datetime.now().isoformat()} | {msg}")

# ---------- SERIAL ----------
ser = serial.Serial(config.PORT, config.BAUD, timeout=1)
time.sleep(2)

# ---------- AT ----------
def send_at(cmd, wait=0.4):
    log(f">>> {cmd}")
    ser.write((cmd + "\r").encode())
    time.sleep(wait)
    while ser.in_waiting:
        log(f"<<< {ser.readline().decode(errors='ignore').strip()}")

# ---------- MODEM INIT ----------
def init_modem():
    send_at("AT")
    send_at("ATE0")
    send_at("AT+CMGF=1")
    send_at('AT+CSCS="GSM"')
    send_at('AT+CPMS="SM","SM","SM"')
    send_at("AT+CNMI=2,1,0,0,0")
    send_at("AT+CLIP=1")
    
    # Check SIM memory status
    ser.write(b"AT+CPMS?\r")
    time.sleep(1)
    memory_status = ""
    while ser.in_waiting:
        line = ser.readline().decode(errors="ignore").strip()
        if line:
            memory_status += line + " "
    log_system(f"SIM Memory: {memory_status}")
    
    # Delete all sent items to free memory
    send_at("AT+CMGD=4,4")
    
    log_system("Modem initialized")

# ---------- DAILY MASTER SENDER ----------
def run_daily_master():
    now = datetime.now()
    today = now.date().isoformat()
    current_time = now.strftime("%H:%M")

    if current_time in config.DAILY_TIMES:
        key = f"{today}-{current_time}"
        if last_daily_sent.get(key):
            return

        msg = random.choice(config.DAILY_MSG)
        send_sms(config.MASTER, msg)
        send_sms(config.ANU, msg)
        last_daily_sent[key] = True

# ---------- CONTEXT ----------
def load_context(number):
    cutoff = datetime.now() - timedelta(hours=config.CONTEXT_HOURS)
    convo = []
    for path in [RECEIVED_LOG, SENT_LOG]:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                try:
                    ts = datetime.fromisoformat(line.split("|")[0].strip())
                    if ts < cutoff or number not in line:
                        continue
                    msg = line.split("|", 2)[-1].strip()
                    convo.append(msg)
                except:
                    pass
    return "\n".join(convo)[-config.MAX_CONTEXT_CHARS:]

# ---------- SHORT CODE DETECTION ----------
def is_short_code(number):
    # Short codes are alphanumeric and don't start with +
    # Normal numbers start with + and are all digits
    if not number:
        return False
    if number.startswith("+"):
        return False
    # If it contains letters, it's a short code
    return any(c.isalpha() for c in number)

def is_non_numerical_sender(number):
    # Non-numerical senders are pure text (no digits), like "BSNL", "BT-SATHI"
    if not number:
        return False
    if number.startswith("+"):
        return False
    # If it contains NO digits, it's a non-numerical sender
    return not any(c.isdigit() for c in number)

# ---------- SMS ----------
def read_sms(index):
    log(f">>> AT+CMGR={index}")
    ser.write(f"AT+CMGR={index}\r".encode())
    lines = []
    start = time.time()
    while time.time() - start < 5:
        l = ser.readline().decode(errors="ignore").strip()
        if l:
            log(f"<<< {l}")
            lines.append(l)
        if l == "OK":
            break
    return "\n".join(lines)

def delete_sms(index):
    send_at(f"AT+CMGD={index}")

def extract_sms(raw):
    lines = raw.splitlines()
    header = next((l for l in lines if l.startswith("+CMGR:")), None)
    if not header:
        return None, None
    # Try to extract numerical number first
    m = re.search(r'"(\+?\d+)"', header)
    number = m.group(1) if m else None
    # If no numerical number, try to extract alphanumeric sender
    if not number:
        m = re.search(r'"([^"]+)"', header)
        number = m.group(1) if m else None
    body = []
    collect = False
    for l in lines:
        if l == header:
            collect = True
            continue
        if collect and l != "OK":
            body.append(l)
    return number, "\n".join(body).strip()

# ---------- SMS SEND ----------
def send_sms(number, text):
    text = text[:config.MAX_SMS_LEN]
    log(f"📤 Sending SMS to {number}")
    log(f"📄 {text}")
    ser.write(f'AT+CMGS="{number}"\r'.encode())
    time.sleep(1)
    while ser.in_waiting:
        log(f"<<< {ser.readline().decode(errors='ignore').strip()}")
    ser.write(text.encode())
    ser.write(b"\x1A")
    # Wait for response with timeout
    start = time.time()
    while time.time() - start < 10:
        if ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()
            log(f"<<< {line}")
            if line == "OK":
                break
        time.sleep(0.1)

# ---------- TELEGRAM ----------
def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{config.TELE_BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": config.TELE_GROUP_ID,
            "text": text
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            log(f"📤 Telegram message sent: {text}")
        else:
            log_system(f"Telegram error: {response.status_code} - {response.text}")
    except Exception as e:
        log_system(f"Telegram send error: {e}")

# ---------- TWO-RING ----------
def handle_ring(caller):
    # Handle MUSE calls - answer, send drive link, hang up
    if caller == config.MUSE:
        send_at("ATA")
        time.sleep(2)
        muse_drive_msg = "Here's all you need:-\nhttps://drive.google.com/drive/folders/1hl5_t0RAu76hMF6KtdCQIVWOumtKuGgV?usp=sharing"
        send_sms(config.MUSE, muse_drive_msg)
        send_at("ATH")
        log_system(f"MUSE call → sending drive link")
        return

    # Handle BASKARAN calls - 1 ring then send MOTOR ON via Telegram
    if caller == config.BASKARAN1 or caller == config.BASKARAN2:
        send_at("ATH")
        send_motor_on_via_user()
        log_system(f"BASKARAN call detected → sending MOTOR ON via user")
        return

    # Handle MASTER calls - disconnect and send random MUSE message
    if caller == config.MASTER:
        send_at("ATH")
        msg = random.choice(config.MUSE_MESSAGES)
        send_sms(config.MUSE, msg)
        log_system(f"MASTER call → sending to MUSE: {msg}")
        return

def send_motor_on_via_user():
    try:
        script_path = os.path.join(os.path.dirname(__file__), "send_motor_on.py")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            log(f"📤 MOTOR ON via user OK: {result.stdout.strip()}")
        else:
            log_system(f"send_motor_on.py failed rc={result.returncode}: {result.stderr.strip()}")
    except Exception as e:
        log_system(f"MOTOR ON user send error: {e}")

# ---------- AI ----------
def ask_ai(prompt, context):
    try:
        r = client.chat.completions.create(
            model=config.MODEL,
            messages=[
                {"role": "system", "content": "Reply via SMS under 140 characters."},
                {"role": "user", "content": context},
                {"role": "user", "content": prompt}
            ],
            max_tokens=80,
            temperature=0.3
        )
        return r.choices[0].message.content.strip()[:config.MAX_SMS_LEN]
    except Exception as e:
        log_system(f"OpenAI API error: {e}")
        return "AI error. Try again later."

def regenerate_lists():
    try:
        log("🔄 Regenerating DAILY_MSG...")
        r = client.chat.completions.create(
            model=config.MODEL,
            messages=[{"role": "user", "content": DAILY_MSG_PROMPT}],
            max_tokens=2000,
            temperature=0.7
        )
        daily_content = r.choices[0].message.content.strip()
        log(f"📝 DAILY raw output (first 200 chars): {daily_content[:200]}")
        
        daily_list = parse_list(daily_content)
        
        if not daily_list:
            log_system(f"DAILY parse failed. Raw: {daily_content[:500]}")
        
        return daily_list
    except Exception as e:
        log_system(f"List regeneration error: {e}")
        return None

def parse_list(content):
    # Remove markdown code blocks if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("python"):
            content = content[6:]
    content = content.strip()
    
    # Try to evaluate as Python list
    try:
        lst = eval(content)
        if isinstance(lst, list):
            return lst
    except:
        pass
    
    # Fallback: extract quoted strings
    import ast
    try:
        lst = ast.literal_eval(content)
        if isinstance(lst, list):
            return lst
    except:
        pass
    
    return None

def update_config_file(new_daily):
    try:
        config_path = os.path.abspath(config.__file__)
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Replace DAILY_MSG
        daily_start = content.find("DAILY_MSG = [")
        if daily_start != -1:
            daily_end = content.find("]", daily_start) + 1
            new_daily_str = "DAILY_MSG = " + str(new_daily)
            content = content[:daily_start] + new_daily_str + content[daily_end:]
        
        with open(config_path, 'w') as f:
            f.write(content)
        
        log_system("Config file updated successfully")
        return True
    except Exception as e:
        log_system(f"Config update error: {e}")
        return False

def reload_config():
    global config
    importlib.reload(config)
    log_system("Config reloaded")

# ---------- BRLOG TELEGRAM POLLING ----------
def get_error_flag():
    try:
        if os.path.exists(BRLOG_ERROR_FLAG):
            with open(BRLOG_ERROR_FLAG, 'r') as f:
                return f.read().strip() == "1"
    except:
        pass
    return False

def set_error_flag(is_error):
    try:
        with open(BRLOG_ERROR_FLAG, 'w') as f:
            f.write("1" if is_error else "0")
    except Exception as e:
        log_system(f"Error flag save error: {e}")

def check_telegram_brlog():
    try:
        script_path = os.path.join(os.path.dirname(__file__), "poll_telegram_brlog.py")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            log_system(f"Telethon poll failed: {result.stderr.strip()}")
            return
        
        if not result.stdout.strip():
            return
        
        import json
        messages = json.loads(result.stdout)
        
        if not messages:
            return
        
        log(f"📥 Telegram BRLog messages: {len(messages)}")
        
        # Track processed message IDs
        processed_file = f"{config.LOG_BASE}/brlog_processed.txt"
        processed_ids = set()
        if os.path.exists(processed_file):
            with open(processed_file, 'r') as f:
                processed_ids = set(line.strip() for line in f if line.strip())
        
        # Filter to new messages only
        new_messages = [msg for msg in messages if str(msg['id']) not in processed_ids]
        
        if not new_messages:
            return
        
        # Check for ERROR and NORMAL keywords in NEW messages only
        has_error = any("ERROR" in msg['text'] for msg in new_messages)
        has_normal = any("NORMAL" in msg['text'] for msg in new_messages)
        
        # Get current error flag state
        error_flag = get_error_flag()
        
        # Logic (applies to NEW messages only):
        # 1. No flag + ERROR (no NORMAL in new messages) → Send ERROR once, raise flag
        # 2. Flag set + NORMAL (in new messages) → Send NORMAL, clear flag
        # 3. No flag + NORMAL (in new messages) → Send NORMAL once (no flag change)
        # 4. Flag set + ERROR (in new messages) → Do nothing (already alerted)
        
        if not error_flag and has_error and not has_normal:
            # First ERROR in new messages, no NORMAL - alert and set flag
            error_msg = next((msg for msg in new_messages if "ERROR" in msg['text']), None)
            if error_msg:
                truncated_text = error_msg['text'][:config.MAX_SMS_LEN]
                send_sms(config.MASTER, f"[BRLog ERROR] {truncated_text}")
                log_system(f"BRLog ERROR sent to MASTER (flag raised)")
                set_error_flag(True)
        elif error_flag and has_normal:
            # Flag was set, now NORMAL received - clear flag and send NORMAL
            normal_msg = next((msg for msg in new_messages if "NORMAL" in msg['text']), None)
            if normal_msg:
                truncated_text = normal_msg['text'][:config.MAX_SMS_LEN]
                send_sms(config.MASTER, f"[BRLog NORMAL] {truncated_text}")
                log_system(f"BRLog NORMAL sent to MASTER (flag cleared)")
                set_error_flag(False)
        elif not error_flag and has_normal:
            # No flag, NORMAL received - just send it once
            normal_msg = next((msg for msg in new_messages if "NORMAL" in msg['text']), None)
            if normal_msg:
                truncated_text = normal_msg['text'][:config.MAX_SMS_LEN]
                send_sms(config.MASTER, f"[BRLog NORMAL] {truncated_text}")
                log_system(f"BRLog NORMAL sent to MASTER (no flag change)")
        
        # Mark all messages as processed
        for msg in messages:
            msg_id = str(msg['id'])
            processed_ids.add(msg_id)
        
        # Save processed IDs
        with open(processed_file, 'w') as f:
            for pid in processed_ids:
                f.write(f"{pid}\n")
                
    except Exception as e:
        log_system(f"Telegram BRLog check error: {e}")

# ---------- MAIN ----------
init_modem()
send_sms(config.ADMIN_NUMBER, f"SMS AI Gateway started ({datetime.now().strftime('%H:%M')})")
log("📡 SMS AI Gateway RUNNING...")

while True:
    try:
        run_daily_master()
        
        # Check Telegram BRLog every 10 minutes
        now = time.time()
        if now - last_telegram_check > 600:
            check_telegram_brlog()
            last_telegram_check = now

        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            time.sleep(1)
            continue

        log(f"<<< {line}")

        # Log RING to system log for visibility
        if "RING" in line:
            log_system(f"Modem RING detected")

        if line.startswith("+CLIP:"):
            m = re.search(r'"(\+?\d+)"', line)
            if m:
                caller = m.group(1)
                log(f"📞 Caller ID detected: {caller}")
                handle_ring(caller)
            else:
                log(f"⚠️ Could not extract number from CLIP: {line}")
            continue

        if "+CMTI" in line:
            idx = line.split(",")[1]
            log_system(f"SMS received at index {idx}")
            raw = read_sms(idx)
            sender, msg = extract_sms(raw)
            delete_sms(idx)

            if not sender or not msg:
                log_system(f"SMS extraction failed for index {idx}")
                continue

            log_file(RECEIVED_LOG, f"{datetime.now().isoformat()} | FROM:{sender} | {msg}")

            # Handle MASTER commands
            if sender == config.MASTER and msg.lower().strip() == "change list":
                log("🔄 MASTER requested list update")
                new_daily = regenerate_lists()
                if new_daily:
                    if update_config_file(new_daily):
                        reload_config()
                        send_sms(config.MASTER, f"✅ DAILY_MSG updated! {len(new_daily)} quotes")
                    else:
                        send_sms(config.MASTER, "❌ Failed to update config file")
                else:
                    send_sms(config.MASTER, "❌ Failed to regenerate list")
                continue

            # Handle MASTER "vroom" command
            if sender == config.MASTER and msg.lower().strip() == "vroom":
                log("🚗 MASTER sent vroom command")
                send_motor_on_via_user()
                send_sms(config.MASTER, "✅ MOTOR ON sent to group")
                continue

            # Handle MASTER "ip" command
            if sender == config.MASTER and (msg.strip() == "ip" or msg.strip() == "Ip" or msg.strip() == "IP"):
                log("🌐 MASTER requested IP address")
                try:
                    result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
                    ip_address = result.stdout.strip().split()[0]
                    send_sms(config.MASTER, f"🌐 Pi IP: {ip_address}")
                except Exception as e:
                    send_sms(config.MASTER, f"❌ Failed to get IP: {e}")
                continue

            # Handle MASTER "reboot" command
            if sender == config.MASTER and msg.lower().strip() == "reboot":
                log("🔄 MASTER requested reboot")
                send_sms(config.MASTER, "🔄 Rebooting Pi now...")
                subprocess.run(["sudo", "reboot"])
                continue

            # Forward non-numerical sender messages to MASTER
            if is_non_numerical_sender(sender):
                log(f"📨 Non-numerical sender detected, forwarding to MASTER")
                log_file(SENT_LOG, f"{datetime.now().isoformat()} | TO:{config.MASTER} | [FWD FROM {sender}] {msg}")
                send_sms(config.MASTER, f"[FWD FROM {sender}] {msg}")
                continue

            # Forward short code messages to MASTER
            if is_short_code(sender):
                log(f"📨 Short code detected, forwarding to MASTER")
                log_file(SENT_LOG, f"{datetime.now().isoformat()} | TO:{config.MASTER} | [FWD FROM {sender}] {msg}")
                send_sms(config.MASTER, f"[FWD FROM {sender}] {msg}")
                continue

            context = load_context(sender)
            reply = ask_ai(msg, context)

            log_file(SENT_LOG, f"{datetime.now().isoformat()} | TO:{sender} | {reply}")
            send_sms(sender, reply)

    except Exception as e:
        log_system(f"Main loop error: {e}")
        time.sleep(2)