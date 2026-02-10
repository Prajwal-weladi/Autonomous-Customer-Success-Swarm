"""
Policy evaluation service with order context and date-based eligibility checking.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

from ..core.logger import setup_logger
from ..core.models import PolicyEvaluationOutput, OrderDetails
from ..rag.service import rag_service
from ..core.models import QueryRequest


logger = setup_logger(__name__)


class PolicyEvaluator:
    """Evaluates policy compliance based on order details and dates."""
    
    def __init__(self):
        self.today = datetime.now().date()
        logger.info("Initialized PolicyEvaluator")
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str or date_str.lower() == "none":
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Failed to parse date: {date_str}")
            return None
    
    def _extract_days_from_policy(self, policy_text: str) -> Optional[int]:
        """
        Extract number of days from policy text.
        
        Examples:
        - "within 7 days" -> 7
        - "30 days from delivery" -> 30
        - "14-day return window" -> 14
        """
        # Common patterns for days
        patterns = [
            r'within\s+(\d+)\s+days',
            r'(\d+)\s+days?\s+(?:of|from|after)',
            r'(\d+)-day',
            r'up\s+to\s+(\d+)\s+days'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, policy_text.lower())
            if match:
                days = int(match.group(1))
                logger.debug(f"Extracted {days} days from policy")
                return days
        
        # Default if not found
        logger.warning("Could not extract days from policy, using default 7 days")
        return 7
    
    def _calculate_days_since_delivery(
        self,
        delivered_date: Optional[str]
    ) -> Optional[int]:
        """Calculate days since delivery."""
        if not delivered_date or delivered_date.lower() == "none":
            return None
        
        delivery_dt = self._parse_date(delivered_date)
        if not delivery_dt:
            return None
        
        days_diff = (self.today - delivery_dt.date()).days
        return days_diff
    
    def _calculate_days_since_order(self, order_date: str) -> int:
        """Calculate days since order was placed."""
        order_dt = self._parse_date(order_date)
        if not order_dt:
            return 0
        
        return (self.today - order_dt.date()).days
    
    def _can_cancel_order(
        self,
        status: str,
        order_date: str,
        policy_text: str
    ) -> tuple[bool, str]:
        """
        Determine if order can be cancelled.
        
        Returns:
            Tuple of (can_cancel, reason)
        """
        status_lower = status.lower()
        
        # Cannot cancel if already delivered
        if status_lower == "delivered":
            return False, "Order has already been delivered. Cancellation is not possible after delivery."
        
        # Cannot cancel if already cancelled
        if status_lower == "cancelled":
            return False, "Order is already cancelled."
        
        # Can cancel if processing or shipped (depending on policy)
        if status_lower in ["processing", "pending"]:
            return True, "Order is still being processed and can be cancelled."
        
        if status_lower == "shipped":
            # Check if policy allows cancellation after shipping
            if "cancel" in policy_text.lower() and "shipped" in policy_text.lower():
                if "cannot" in policy_text.lower() or "not allowed" in policy_text.lower():
                    return False, "Order has been shipped. Our policy does not allow cancellation once an order is shipped."
                else:
                    return True, "Order has been shipped but can still be cancelled as per our policy."
            else:
                # Default: cannot cancel once shipped
                return False, "Order has been shipped. Cancellation is typically not possible once an order is in transit."
        
        # Default
        return True, "Order can be cancelled as it has not been delivered yet."
    
    def _can_exchange_or_return(
        self,
        delivered_date: Optional[str],
        status: str,
        policy_text: str,
        action: str = "exchange"
    ) -> tuple[bool, str]:
        """
        Determine if item can be exchanged or returned.
        
        Args:
            delivered_date: Date when order was delivered
            status: Current order status
            policy_text: Relevant policy text
            action: "exchange" or "return"
        
        Returns:
            Tuple of (allowed, reason)
        """
        status_lower = status.lower()
        
        # Must be delivered for exchange/return
        if status_lower != "delivered":
            if not delivered_date or delivered_date.lower() == "none":
                return False, f"Order has not been delivered yet (current status: {status}). {action.title()} is only possible after delivery."
        
        # Calculate days since delivery
        days_since_delivery = self._calculate_days_since_delivery(delivered_date)
        
        if days_since_delivery is None:
            return False, f"Order has not been delivered yet. {action.title()} is only available after delivery."
        
        # Extract allowed days from policy
        allowed_days = self._extract_days_from_policy(policy_text)
        
        # Check if within allowed period
        if days_since_delivery <= allowed_days:
            remaining_days = allowed_days - days_since_delivery
            return True, f"Item was delivered {days_since_delivery} days ago. {action.title()} is allowed within {allowed_days} days of delivery. You have {remaining_days} days remaining."
        else:
            delivered_dt = self._parse_date(delivered_date)
            if delivered_dt:
                expiry_date = (delivered_dt + timedelta(days=allowed_days)).strftime("%Y-%m-%d")
                return False, f"Item was delivered {days_since_delivery} days ago (on {delivered_date}). Our policy allows {action} only within {allowed_days} days of delivery. The {action} period expired on {expiry_date}."
            else:
                return False, f"Item was delivered {days_since_delivery} days ago. Our policy allows {action} only within {allowed_days} days of delivery. The {action} period has expired."
    
    def evaluate_policy(
        self,
        query: str,
        order_details,
        policy_text: str,
        state
    ) -> PolicyEvaluationOutput:
        """
        Evaluate policy compliance based on order details from state.
        
        Args:
            query: User query
            order_details: Order information (from state["entities"]["order_details"])
            policy_text: Retrieved policy text
            state: Current orchestrator state with triage + database results
        
        Returns:
            PolicyEvaluationOutput with structured decision
        """
        # Extract order_details from state - these are updated from triage + database agents
        od = state.get("entities", {}).get("order_details", order_details) if state else order_details
        
        # Handle both dict and Pydantic model formats
        order_id = od.get("order_id") if isinstance(od, dict) else od.order_id
        status = od.get("status") if isinstance(od, dict) else od.status
        order_date = od.get("order_date") if isinstance(od, dict) else od.order_date
        delivered_date = od.get("delivered_date") if isinstance(od, dict) else od.delivered_date
        
        logger.info(f"Evaluating policy for order {order_id}")
        
        # Determine intent from query
        query_lower = query.lower()
        is_exchange_query = any(word in query_lower for word in ["exchange", "swap", "change size", "different size"])
        is_return_query = any(word in query_lower for word in ["return", "refund", "send back"])
        is_cancel_query = any(word in query_lower for word in ["cancel", "cancellation"])
        
        # Evaluate cancellation
        can_cancel, cancel_reason = self._can_cancel_order(
            status,
            order_date,
            policy_text
        )
        
        # Evaluate exchange/return
        can_exchange, exchange_reason = self._can_exchange_or_return(
            delivered_date,
            status,
            policy_text,
            action="exchange"
        )
        
        # Determine primary reason based on query intent
        if is_cancel_query:
            primary_reason = cancel_reason
        elif is_exchange_query or is_return_query:
            primary_reason = exchange_reason
        else:
            # Default: provide both
            if not can_cancel and not can_exchange:
                primary_reason = f"{cancel_reason} Additionally, {exchange_reason.lower()}"
            elif can_exchange and not can_cancel:
                primary_reason = f"{exchange_reason} However, {cancel_reason.lower()}"
            elif can_cancel and not can_exchange:
                primary_reason = f"{cancel_reason} However, {exchange_reason.lower()}"
            else:
                primary_reason = f"{exchange_reason} {cancel_reason}"
        
        # Create output
        output = PolicyEvaluationOutput(
            policy=policy_text[:500] + "..." if len(policy_text) > 500 else policy_text,
            exchange_allowed=can_exchange,
            cancel_allowed=can_cancel,
            reason=primary_reason
        )
        
        logger.info(
            f"Policy evaluation complete: exchange={can_exchange}, "
            f"cancel={can_cancel}"
        )
        
        return output


class EnhancedPolicyService:
    """Enhanced RAG service with order context evaluation."""
    
    def __init__(self):
        self.evaluator = PolicyEvaluator()
        logger.info("Initialized EnhancedPolicyService")
    
    def query_with_order_context(
        self,
        query: str,
        state,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> PolicyEvaluationOutput:
        """
        Query policy with order context and return structured evaluation.
        
        Args:
            query: User query
            state: Orchestrator state containing order_details from triage + database
            conversation_history: Previous messages
        
        Returns:
            PolicyEvaluationOutput with structured decision
        """
        # Extract order_details from state (set by database agent)
        order_details = state.get("entities", {}).get("order_details")
        
        if not order_details:
            logger.error("order_details not found in state")
            raise ValueError("order_details not found in state")
        
        logger.info(f"Processing query with order context: order_id={order_details.get('order_id') if isinstance(order_details, dict) else order_details.order_id}")
        
        # Ensure RAG service is initialized
        if not rag_service._initialized:
            rag_service.initialize()
        
        # Enhance query with order context
        enhanced_query = self._create_enhanced_query(query, order_details, state)
        
        # Query RAG system for relevant policy
        rag_request = QueryRequest(
            query=enhanced_query,
            conversation_history=conversation_history or []
        )
        
        rag_response = rag_service.query(rag_request)
        policy_text = rag_response.answer
        
        # If no policy found, use generic text
        if "don't have enough information" in policy_text.lower():
            policy_text = "Standard return and exchange policy: Items can be returned or exchanged within 7 days of delivery if unused and in original packaging. Cancellation is allowed before shipment."
        
        # Evaluate policy compliance
        evaluation = self.evaluator.evaluate_policy(
            query=query,
            order_details=order_details,
            state=state,
            policy_text=policy_text
        )
        
        return evaluation
    
    def _create_enhanced_query(
        self,
        query: str,
        order_details,
        state
    ) -> str:
        """Create enhanced query with order context extracted from state."""
        # Extract order_details from state - could be dict or OrderDetails model
        od = state.get("entities", {}).get("order_details", order_details)
        
        # Handle both dict and Pydantic model
        product = od.get("product") if isinstance(od, dict) else od.product
        status = od.get("status") if isinstance(od, dict) else od.status
        delivered_date = od.get("delivered_date") if isinstance(od, dict) else od.delivered_date
        
        # Determine query type
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["exchange", "swap", "change"]):
            policy_type = "exchange"
        elif any(word in query_lower for word in ["return", "refund"]):
            policy_type = "return"
        elif any(word in query_lower for word in ["cancel"]):
            policy_type = "cancellation"
        else:
            policy_type = "return and exchange"
        
        # Create context-aware query using values from state
        enhanced = f"What is the {policy_type} policy for {product}? "
        enhanced += f"The order status is {status}. "
        
        if delivered_date and delivered_date.lower() != "none":
            enhanced += f"The item was delivered on {delivered_date}. "
        
        enhanced += f"How many days are allowed for {policy_type}?"
        
        logger.debug(f"Enhanced query: {enhanced}")
        return enhanced


# Global service instance
enhanced_policy_service = EnhancedPolicyService()