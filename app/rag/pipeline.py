"""
Advanced RAG pipeline with query translation, routing, retrieval, and re-ranking.
"""
from typing import List, Dict, Tuple, Optional
import time

from app.core.config import settings
from app.core.logger import setup_logger
from app.core.models import DocumentChunk, RetrievedContext
from app.rag.embedding import FAISSVectorStore
from app.rag.llm import OllamaClient
from app.prompts.rag_prompts import (
    QUERY_TRANSLATION_PROMPT,
    QUERY_ROUTING_PROMPT,
    RERANKING_PROMPT,
    ANSWER_GENERATION_PROMPT,
    format_conversation_history,
    format_context_chunks
)


logger = setup_logger(__name__)


class AdvancedRAGPipeline:
    """Advanced RAG pipeline with multiple optimization stages."""
    
    def __init__(
        self,
        vector_store: FAISSVectorStore,
        llm_client: OllamaClient
    ):
        self.vector_store = vector_store
        self.llm_client = llm_client
        
        logger.info("Initialized AdvancedRAGPipeline")
    
    def translate_query(
        self,
        query: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Translate/optimize user query for better retrieval.
        
        Args:
            query: Original user query
            conversation_history: Previous conversation messages
        
        Returns:
            Translated query
        """
        logger.debug("Translating query")
        
        # Format conversation history
        history_text = format_conversation_history(conversation_history)
        
        # Build prompt
        prompt = QUERY_TRANSLATION_PROMPT.format(
            original_query=query,
            conversation_history=history_text
        )
        
        try:
            # Generate translation
            translated = self.llm_client.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=100
            )
            
            logger.info(f"Query translation: '{query}' -> '{translated}'")
            return translated
            
        except Exception as e:
            logger.error(f"Query translation failed: {str(e)}")
            # Fallback to original query
            return query
    
    def route_query(
        self,
        query: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Route query to appropriate policy domain.
        
        Args:
            query: User query
            conversation_history: Previous conversation messages
        
        Returns:
            Selected policy domain
        """
        logger.debug("Routing query to domain")
        
        # Format conversation history
        history_text = format_conversation_history(conversation_history)
        
        # Build prompt
        prompt = QUERY_ROUTING_PROMPT.format(
            query=query,
            conversation_history=history_text
        )
        
        try:
            # Generate routing decision
            domain = self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=20
            )
            
            # Clean and validate domain
            domain = domain.strip().lower()
            
            # Validate against known domains
            valid_domains = settings.POLICY_DOMAINS
            if domain not in valid_domains:
                logger.warning(
                    f"Invalid domain '{domain}', defaulting to 'general'"
                )
                domain = "general"
            
            logger.info(f"Query routed to domain: '{domain}'")
            return domain
            
        except Exception as e:
            logger.error(f"Query routing failed: {str(e)}")
            # Fallback to general
            return "general"
    
    def retrieve_contexts(
        self,
        query: str,
        filter_domain: Optional[str] = None,
        k: int = settings.TOP_K_RETRIEVAL
    ) -> List[RetrievedContext]:
        """
        Retrieve relevant contexts from vector store.
        
        Args:
            query: Search query
            filter_domain: Optional domain filter
            k: Number of results
        
        Returns:
            List of RetrievedContext objects
        """
        logger.debug(f"Retrieving top-{k} contexts")
        
        # Search vector store
        results = self.vector_store.search(
            query=query,
            k=k,
            filter_domain=filter_domain
        )
        
        # Convert to RetrievedContext objects
        contexts = []
        for chunk, score in results:
            context = RetrievedContext(
                content=chunk.content,
                policy_domain=chunk.policy_domain,
                source_url=chunk.source_url,
                relevance_score=score,
                metadata=chunk.metadata
            )
            contexts.append(context)
        
        logger.info(f"Retrieved {len(contexts)} contexts")
        return contexts
    
    def rerank_contexts(
        self,
        query: str,
        contexts: List[RetrievedContext],
        top_k: int = settings.TOP_K_RERANK
    ) -> List[RetrievedContext]:
        """
        Re-rank contexts using LLM-based relevance scoring.
        
        Args:
            query: User query
            contexts: Retrieved contexts
            top_k: Number of top contexts to keep
        
        Returns:
            Re-ranked list of contexts
        """
        logger.debug(f"Re-ranking {len(contexts)} contexts")
        
        if len(contexts) <= top_k:
            return contexts
        
        scored_contexts = []
        
        for context in contexts:
            try:
                # Build prompt
                prompt = RERANKING_PROMPT.format(
                    query=query,
                    chunk_content=context.content
                )
                
                # Generate score
                score_text = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.1,
                    max_tokens=10
                )
                
                # Parse score
                try:
                    score = float(score_text.strip())
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                except ValueError:
                    logger.warning(
                        f"Failed to parse relevance score: '{score_text}'"
                    )
                    score = context.relevance_score  # Use original score
                
                # Update relevance score
                context.relevance_score = score
                scored_contexts.append(context)
                
            except Exception as e:
                logger.error(f"Re-ranking failed for context: {str(e)}")
                # Keep original score
                scored_contexts.append(context)
        
        # Sort by relevance score (descending)
        scored_contexts.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Return top-k
        top_contexts = scored_contexts[:top_k]
        
        logger.info(
            f"Re-ranked to top-{top_k} contexts with scores: "
            f"{[f'{c.relevance_score:.3f}' for c in top_contexts]}"
        )
        
        return top_contexts
    
    def generate_answer(
        self,
        query: str,
        contexts: List[RetrievedContext],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate final answer from contexts.
        
        Args:
            query: User query
            contexts: Retrieved and re-ranked contexts
            conversation_history: Previous conversation messages
        
        Returns:
            Generated answer text
        """
        logger.debug("Generating final answer")
        
        # Format contexts
        context_texts = [c.content for c in contexts]
        context_str = format_context_chunks(context_texts)
        
        # Format conversation history
        history_text = format_conversation_history(conversation_history)
        
        # Build prompt
        prompt = ANSWER_GENERATION_PROMPT.format(
            query=query,
            conversation_history=history_text,
            context=context_str
        )
        
        try:
            # Generate answer
            answer = self.llm_client.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=settings.GENERATION_MAX_TOKENS
            )
            
            logger.info("Answer generated successfully")
            return answer
            
        except Exception as e:
            logger.error(f"Answer generation failed: {str(e)}")
            return "I apologize, but I encountered an error generating a response. Please try again."
    
    def query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filter_domain: Optional[str] = None,
        use_query_translation: bool = True,
        use_query_routing: bool = True,
        use_reranking: bool = True
    ) -> str:
        """
        Execute full RAG pipeline.
        
        Args:
            query: User query
            conversation_history: Previous conversation messages
            filter_domain: Optional domain filter (overrides routing)
            use_query_translation: Enable query translation
            use_query_routing: Enable query routing
            use_reranking: Enable context re-ranking
        
        Returns:
            Generated answer text
        """
        start_time = time.time()
        conversation_history = conversation_history or []
        
        logger.info(f"Processing query: '{query}'")
        
        # Step 1: Query Translation (optional)
        if use_query_translation:
            translated_query = self.translate_query(query, conversation_history)
        else:
            translated_query = query
        
        # Step 2: Query Routing (optional, unless domain is specified)
        if filter_domain:
            selected_domain = filter_domain
            logger.info(f"Using specified domain: '{selected_domain}'")
        elif use_query_routing:
            selected_domain = self.route_query(query, conversation_history)
        else:
            selected_domain = None
        
        # Step 3: Retrieval
        contexts = self.retrieve_contexts(
            query=translated_query,
            filter_domain=selected_domain,
            k=settings.TOP_K_RETRIEVAL
        )
        
        if not contexts:
            logger.warning("No contexts retrieved")
            return "I don't have enough information in the policies to answer this question."
        
        # Step 4: Re-ranking (optional)
        if use_reranking:
            contexts = self.rerank_contexts(
                query=query,
                contexts=contexts,
                top_k=settings.TOP_K_RERANK
            )
        else:
            # Just take top-k
            contexts = contexts[:settings.TOP_K_RERANK]
        
        # Step 5: Generate Answer
        answer = self.generate_answer(
            query=query,
            contexts=contexts,
            conversation_history=conversation_history
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Query processed in {elapsed:.2f}s")
        
        return answer