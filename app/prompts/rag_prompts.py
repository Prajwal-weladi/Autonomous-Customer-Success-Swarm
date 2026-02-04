"""
Prompt templates for the RAG pipeline.
"""
from typing import List, Dict


# Query Translation
QUERY_TRANSLATION_PROMPT = """You are a query optimization expert. Your task is to reformulate user queries to be more effective for semantic search in a policy document database.

Original Query: {original_query}

Conversation History:
{conversation_history}

Instructions:
1. Analyze the original query and conversation context
2. Reformulate the query to be more specific and search-friendly
3. Expand abbreviations and add relevant context
4. Keep the core intent but make it clearer
5. Return ONLY the reformulated query text, nothing else

Reformulated Query:"""


# Query Routing
QUERY_ROUTING_PROMPT = """You are a query routing expert for a customer service policy system. Your task is to determine which policy domain best matches the user's query.

Available Policy Domains:
- returns: Product returns, return eligibility, return process
- refund: Refund policies, refund timelines, refund methods
- shipping: Shipping policies, delivery times, shipping costs
- cancellation: Order cancellation, cancellation policies
- warranty: Product warranties, warranty claims
- terms: Terms of service, general terms and conditions
- privacy: Privacy policy, data protection
- general: General policies that don't fit other categories

User Query: {query}

Conversation History:
{conversation_history}

Instructions:
1. Analyze the query and determine the most relevant policy domain
2. Consider conversation context if available
3. Choose exactly ONE domain from the list above
4. Respond ONLY with the domain name, nothing else

Selected Domain:"""


# Re-ranking
RERANKING_PROMPT = """You are a relevance scoring expert. Your task is to score how relevant each document chunk is to the user's query.

User Query: {query}

Document Chunk:
{chunk_content}

Instructions:
1. Evaluate how well the chunk answers the query
2. Consider semantic relevance, not just keyword matching
3. Score from 0.0 (completely irrelevant) to 1.0 (perfectly relevant)
4. Respond ONLY with a single number between 0.0 and 1.0, nothing else

Relevance Score:"""


# Final Answer Generation
ANSWER_GENERATION_PROMPT = """You are a customer service policy expert. Your task is to provide accurate, helpful answers based STRICTLY on the provided policy documents.

User Query: {query}

Conversation History:
{conversation_history}

Relevant Policy Context:
{context}

CRITICAL INSTRUCTIONS:
1. Answer MUST be based ONLY on the provided policy context
2. If the context doesn't contain enough information, say "I don't have enough information in the policies to answer this question"
3. DO NOT make assumptions or add information not in the context
4. Be concise but complete
5. Use a professional, helpful tone
6. DO NOT include citations, metadata, or reasoning
7. ONLY provide the final answer text
8. DO NOT include phrases like "According to the policy" or "Based on the context"
9. Answer directly as if stating the policy

Your Answer:"""


def format_conversation_history(history: List[Dict[str, str]]) -> str:
    """
    Format conversation history for prompts.
    
    Args:
        history: List of message dictionaries with 'role' and 'content'
    
    Returns:
        Formatted conversation string
    """
    if not history:
        return "No previous conversation."
    
    formatted = []
    for msg in history[-5:]:  # Last 5 messages
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        formatted.append(f"{role.capitalize()}: {content}")
    
    return "\n".join(formatted)


def format_context_chunks(chunks: List[str]) -> str:
    """
    Format context chunks for prompts.
    
    Args:
        chunks: List of chunk content strings
    
    Returns:
        Formatted context string
    """
    if not chunks:
        return "No relevant policy context found."
    
    formatted = []
    for idx, chunk in enumerate(chunks, 1):
        formatted.append(f"[Context {idx}]\n{chunk}\n")
    
    return "\n".join(formatted)