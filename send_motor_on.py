from telethon import TelegramClient
import os
import config

# Replace with your actual values from https://my.telegram.org
API_ID = 33876152  # Your API ID
API_HASH = "87a08340b095a7bfca0af3e16cd781c7"  # Your API Hash
PHONE_NUMBER = "+916379228576"  # Your phone number with country code

CHAT_ID = int(config.MOTOR_TELE_GROUP_ID) if hasattr(config, "MOTOR_TELE_GROUP_ID") else -1003232090112
MISSED_MSG = "MISSED CALL Command Incoming"
MOTOR_ON_MSG = "MOTOR ON"

async def send_message():
    client = TelegramClient('session_name', API_ID, API_HASH)
    
    await client.start(PHONE_NUMBER)
    
    # Send the pre-message first, then MOTOR ON
    await client.send_message(CHAT_ID, MISSED_MSG)
    await client.send_message(CHAT_ID, MOTOR_ON_MSG)
    print("Message sent successfully!")
    
    await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(send_message())
