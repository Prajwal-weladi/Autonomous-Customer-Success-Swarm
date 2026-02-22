import asyncio
from app.api.message import handle_message, MessageRequest
import uuid

async def test():
    req = MessageRequest(
        conversation_id='test-' + str(uuid.uuid4()),
        message='return this order',
        user_email='tester123@example.com'
    )
    r = await handle_message(req)
    print(f'INTENT: {r.intent}')
    print(f'STATUS: {r.status}')
    if getattr(r, 'orders', None):
        print(f'ORDERS_COUNT: {len(r.orders)}')
        print(f'FIRST_ORDER_ID: {r.orders[0]["order_id"]}')
    else:
        print(f'ORDER_ID: {getattr(r, "order_id", None)}')
    print(f'REPLY: {r.reply}')

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test())
