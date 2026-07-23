from telethon import TelegramClient
import config
import sys

API_ID = 33876152
API_HASH = "87a08340b095a7bfca0af3e16cd781c7"
PHONE_NUMBER = "+916379228576"
CHAT_ID = int(config.PPMS_TELE_GROUP_ID) if hasattr(config, "PPMS_TELE_GROUP_ID") else -1002942360802

async def poll_messages():
    client = TelegramClient('session_name', API_ID, API_HASH)
    
    try:
        await client.start(PHONE_NUMBER)
        
        # Get last 10 messages from the group
        messages = []
        async for message in client.iter_messages(CHAT_ID, limit=10):
            if message.text and message.text.startswith("BRLog Alert ::"):
                messages.append({
                    'id': message.id,
                    'text': message.text,
                    'date': message.date.isoformat()
                })
        
        # Output as JSON for main script to parse
        import json
        print(json.dumps(messages))
        
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(poll_messages())
