#!/usr/bin/env python3
"""
Example usage of the Policy RAG Agent.
Demonstrates various query patterns and conversation flows.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.rag.service import rag_service
from app.core.models import QueryRequest


def example_simple_query():
    """Example: Simple query without conversation history."""
    print("\n" + "=" * 60)
    print("Example 1: Simple Query")
    print("=" * 60)
    
    request = QueryRequest(
        query="What is the return policy for electronics?",
        conversation_history=[]
    )
    
    response = rag_service.query(request)
    
    print(f"\nQuery: {request.query}")
    print(f"\nAnswer:\n{response.answer}")


def example_conversation():
    """Example: Multi-turn conversation."""
    print("\n" + "=" * 60)
    print("Example 2: Conversation Flow")
    print("=" * 60)
    
    conversation = []
    
    # Turn 1
    query1 = "Tell me about returns"
    request1 = QueryRequest(
        query=query1,
        conversation_history=conversation
    )
    response1 = rag_service.query(request1)
    
    print(f"\nUser: {query1}")
    print(f"Assistant: {response1.answer}")
    
    # Update conversation
    conversation.extend([
        {"role": "user", "content": query1},
        {"role": "assistant", "content": response1.answer}
    ])
    
    # Turn 2
    query2 = "What about electronics specifically?"
    request2 = QueryRequest(
        query=query2,
        conversation_history=conversation
    )
    response2 = rag_service.query(request2)
    
    print(f"\nUser: {query2}")
    print(f"Assistant: {response2.answer}")
    
    # Update conversation
    conversation.extend([
        {"role": "user", "content": query2},
        {"role": "assistant", "content": response2.answer}
    ])
    
    # Turn 3
    query3 = "How long do I have to return it?"
    request3 = QueryRequest(
        query=query3,
        conversation_history=conversation
    )
    response3 = rag_service.query(request3)
    
    print(f"\nUser: {query3}")
    print(f"Assistant: {response3.answer}")


def example_domain_filter():
    """Example: Query with domain filter."""
    print("\n" + "=" * 60)
    print("Example 3: Domain-Specific Query")
    print("=" * 60)
    
    request = QueryRequest(
        query="What are the charges?",
        conversation_history=[],
        filter_domain="shipping"
    )
    
    response = rag_service.query(request)
    
    print(f"\nQuery: {request.query}")
    print(f"Domain Filter: {request.filter_domain}")
    print(f"\nAnswer:\n{response.answer}")


def example_various_queries():
    """Example: Various query types."""
    print("\n" + "=" * 60)
    print("Example 4: Various Query Types")
    print("=" * 60)
    
    queries = [
        "Can I cancel my order?",
        "What is the warranty period?",
        "How long does delivery take?",
        "What items can't be returned?",
        "How do I get a refund?"
    ]
    
    for query in queries:
        request = QueryRequest(
            query=query,
            conversation_history=[]
        )
        
        response = rag_service.query(request)
        
        print(f"\n{'─' * 60}")
        print(f"Q: {query}")
        print(f"A: {response.answer}")


def main():
    """Main function."""
    print("=" * 60)
    print("Policy RAG Agent - Usage Examples")
    print("=" * 60)
    
    # Initialize service
    print("\nInitializing RAG service...")
    rag_service.initialize()
    print("✓ Service initialized")
    
    # Check health
    health = rag_service.get_health()
    print(f"\nService Status:")
    print(f"  - Ollama Connected: {health['ollama_connected']}")
    print(f"  - Index Loaded: {health['index_loaded']}")
    print(f"  - Documents Indexed: {health['documents_indexed']}")
    
    if not health['index_loaded']:
        print("\n⚠ Index not loaded. Please run reindexing first:")
        print("  python -m setup")
        return 1
    
    # Run examples
    try:
        example_simple_query()
        example_conversation()
        example_domain_filter()
        example_various_queries()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed successfully")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error running examples: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())