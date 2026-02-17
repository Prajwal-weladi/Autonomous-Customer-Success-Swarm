# model.py
from typing import Optional
from pydantic import BaseModel

class ResolutionInput(BaseModel):
    order_id: str                   # Order ID (also used as deal_id)
    intent: str                     # Intent: exchange, cancel, refund, etc.
    product: Optional[str] = None   # Product name for return label
    size: Optional[int] = None      # Product size
    amount: Optional[int] = 0
    exchange_allowed: Optional[bool] = None  # From policy agent
    cancel_allowed: Optional[bool] = None    # From policy agent
    reason: Optional[str] = None    # Reason/explanation from policy agent
    status: Optional[str] = None
