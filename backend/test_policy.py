import asyncio
from app.api.message import handle_message, MessageRequest
import uuid

async def test():
    req = MessageRequest(
        conversation_id='test-' + str(uuid.uuid4()),
        message='can you tell me all the policies for refund',
        user_email='tester123@example.com'
    )
    r = await handle_message(req)
    print(f'INTENT: {r.intent}')
    print(f'STATUS: {r.status}')
    print(f'REPLY: {r.reply}')

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test())
