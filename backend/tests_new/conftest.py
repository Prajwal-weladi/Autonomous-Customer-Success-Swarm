"""
Shared fixtures and helpers for the test suite.
"""
import sys
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Ensure the backend root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ──────────────────────── date helpers ────────────────────────────────────────

def days_ago(n: int) -> str:
    """Return a YYYY-MM-DD date string for n days ago."""
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


# ──────────────────────── shared order fixtures ───────────────────────────────

@pytest.fixture
def delivered_recent_order():
    """Order delivered 10 days ago — eligible for refund AND return."""
    return {
        "order_id": "11111",
        "product": "Wireless Headphones",
        "status": "Delivered",
        "order_date": days_ago(20),
        "delivered_date": days_ago(10),
        "amount": 2199,
        "quantity": 1,
    }


@pytest.fixture
def delivered_old_order():
    """Order delivered 35 days ago — eligible for return (45d) but NOT refund (30d)."""
    return {
        "order_id": "22222",
        "product": "Running Shoes",
        "status": "Delivered",
        "order_date": days_ago(50),
        "delivered_date": days_ago(35),
        "amount": 3499,
        "quantity": 1,
    }


@pytest.fixture
def delivered_expired_order():
    """Order delivered 50 days ago — ineligible for both refund AND return."""
    return {
        "order_id": "33333",
        "product": "Smart Watch",
        "status": "Delivered",
        "order_date": days_ago(65),
        "delivered_date": days_ago(50),
        "amount": 8999,
        "quantity": 1,
    }


@pytest.fixture
def shipped_order():
    """Order currently in transit — can be cancelled."""
    return {
        "order_id": "44444",
        "product": "Laptop Bag",
        "status": "Shipped",
        "order_date": days_ago(3),
        "delivered_date": None,
        "amount": 1299,
        "quantity": 1,
    }


@pytest.fixture
def processing_order():
    """Order not yet shipped — eligible for cancellation."""
    return {
        "order_id": "55555",
        "product": "Gaming Mouse",
        "status": "Processing",
        "order_date": days_ago(1),
        "delivered_date": None,
        "amount": 999,
        "quantity": 1,
    }


@pytest.fixture
def cancelled_order():
    """Already-cancelled order."""
    return {
        "order_id": "66666",
        "product": "Keyboard",
        "status": "Cancelled",
        "order_date": days_ago(10),
        "delivered_date": None,
        "amount": 1599,
        "quantity": 1,
    }
