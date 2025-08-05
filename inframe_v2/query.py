#!/usr/bin/env python3
"""
Querier class that uses the Modal query API for video analysis.
Provides a simple interface for asking questions about recorded video content.
"""

import asyncio
import os
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class QueryResult:
    """Result from asking a question about video content"""
    session_id: str
    question: str
    answer: str
    confidence: float
    video_id: str
    frame_count: int
    analysis_success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'question': self.question,
            'answer': self.answer,
            'confidence': self.confidence,
            'video_id': self.video_id,
            'frame_count': self.frame_count,
            'analysis_success': self.analysis_success,
            'error_message': self.error_message
        }


@dataclass
class QueryStats:
    """Statistics about query operations"""
    session_id: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    average_confidence: float
    total_search_operations: int
    total_analysis_operations: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'total_queries': self.total_queries,
            'successful_queries': self.successful_queries,
            'failed_queries': self.failed_queries,
            'average_confidence': self.average_confidence,
            'total_search_operations': self.total_search_operations,
            'total_analysis_operations': self.total_analysis_operations,
            'success_rate': self.successful_queries / max(1, self.total_queries)
        }


class Querier:
    """API-based query interface for video content analysis"""
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize the querier with API-based query capabilities
        
        Args:
            session_id: Session identifier to query (if None, queries all sessions)
        """
        self.session_id = session_id
        
        # Get the query API URL from environment
        self.query_url = os.environ.get("QUERY_URL", "https://adscope--query-service.modal.run")
        self.endpoint_url = self.query_url.replace(".modal.run", "-query-v1.modal.run")
        
        # Statistics tracking
        self.query_stats = QueryStats(
            session_id=self.session_id or "all_sessions",
            total_queries=0,
            successful_queries=0,
            failed_queries=0,
            average_confidence=0.0,
            total_search_operations=0,
            total_analysis_operations=0
        )
        
        print("✅ Querier initialized")
        if self.session_id:
            print(f"   Session ID: {self.session_id}")
        else:
            print("   Session ID: All sessions")
        print("   Query API: Active")
        print(f"   Endpoint: {self.endpoint_url}")
    
    def get_session_id(self) -> Optional[str]:
        """Get the session ID for this querier"""
        return self.session_id
    
    async def ask_question(self, 
                          question: str,
                          top_k: int = 20,
                          min_similarity: float = 0.2,
                          temporal_weight: float = 0.1,
                          max_age_seconds: Optional[float] = None) -> QueryResult:
        """Ask a question about the recorded video content via API
        
        Args:
            question: The question to ask about the video content
            top_k: Maximum number of frames to consider
            min_similarity: Minimum similarity threshold for frame selection
            temporal_weight: Weight for temporal recency (0.0 = no bias, 1.0 = strong bias)
            max_age_seconds: Only consider frames from last N seconds (None = no limit)
            
        Returns:
            QueryResult with the analysis answer and metadata
        """
        
        try:
            session_info = f" (session: {self.session_id})" if self.session_id else ""
            print(f"🤖 Analyzing question: '{question}'{session_info}")
            print("=" * 50)
            
            # Prepare request payload
            payload = {
                "question": question,
                "session_id": self.session_id,
                "top_k": top_k,
                "min_similarity": min_similarity
            }
            
            # Make HTTP POST request to Modal API
            async with httpx.AsyncClient(
                timeout=600.0,
                verify=False,  # Disable SSL verification for testing
                http2=False,   # Disable HTTP/2 to avoid compatibility issues
                follow_redirects=True  # Follow HTTP redirects (like 303)
            ) as client:
                response = await client.post(
                    self.endpoint_url,
                    json=payload
                )
                
                print(f"📡 HTTP Response: {response.status_code}")
                print(f"📡 Response headers: {dict(response.headers)}")
                print(f"📡 Response text preview: {response.text[:200]}...")
                
                if response.status_code == 200:
                    try:
                        api_result = response.json()
                        print(f"📡 JSON parsing successful, keys: {list(api_result.keys()) if isinstance(api_result, dict) else 'Not a dict'}")
                    except Exception as json_error:
                        print(f"❌ JSON parsing failed: {json_error}")
                        print(f"❌ Full response text: {response.text}")
                        raise json_error
                    
                    # Update statistics
                    self.query_stats.total_queries += 1
                    self.query_stats.total_search_operations += 1
                    self.query_stats.total_analysis_operations += 1
                    
                    if api_result.get("success", False):
                        # Success case
                        self.query_stats.successful_queries += 1
                        
                        # Update average confidence
                        confidence = api_result.get("confidence", 0.0)
                        total_confidence = (self.query_stats.average_confidence * 
                                         (self.query_stats.successful_queries - 1) + 
                                         confidence)
                        self.query_stats.average_confidence = total_confidence / self.query_stats.successful_queries
                        
                        result = QueryResult(
                            session_id=self.session_id or "all_sessions",
                            question=question,
                            answer=api_result.get("answer", ""),
                            confidence=confidence,
                            video_id=api_result.get("video_id", ""),
                            frame_count=api_result.get("frame_count", 0),
                            analysis_success=True
                        )
                        
                        print(f"✅ Analysis completed successfully!")
                        print(f"   Confidence: {confidence:.3f}")
                        print(f"   Frames analyzed: {api_result.get('frame_count', 0)}")
                        
                        return result
                    else:
                        # API returned failure
                        self.query_stats.failed_queries += 1
                        
                        result = QueryResult(
                            session_id=self.session_id or "all_sessions",
                            question=question,
                            answer=api_result.get("answer", "No relevant content found to answer this question."),
                            confidence=0.0,
                            video_id="",
                            frame_count=0,
                            analysis_success=False,
                            error_message=api_result.get("error", "API returned failure")
                        )
                        
                        print(f"❌ API returned failure: {api_result.get('error', 'Unknown error')}")
                        return result
                else:
                    # HTTP error
                    self.query_stats.failed_queries += 1
                    self.query_stats.total_queries += 1
                    
                    error_msg = f"HTTP error {response.status_code}: {response.text}"
                    print(f"❌ {error_msg}")
                    
                    result = QueryResult(
                        session_id=self.session_id or "all_sessions",
                        question=question,
                        answer="Unable to analyze the video content due to an HTTP error.",
                        confidence=0.0,
                        video_id="",
                        frame_count=0,
                        analysis_success=False,
                        error_message=error_msg
                    )
                    
                    return result
                
        except Exception as e:
            # Error case
            self.query_stats.failed_queries += 1
            self.query_stats.total_queries += 1
            
            error_msg = f"Error analyzing question: {str(e) if str(e) else 'Unknown exception occurred'}"
            print(f"❌ {error_msg}")
            print(f"❌ Exception type: {type(e).__name__}")
            print(f"❌ Exception details: {repr(e)}")
            
            # Also check if we got a response
            try:
                if 'response' in locals() and hasattr(response, 'text'):
                    print(f"❌ Response text: {response.text[:500]}")  # First 500 chars
            except:
                pass
            
            result = QueryResult(
                session_id=self.session_id or "all_sessions",
                question=question,
                answer="Unable to analyze the video content due to an error.",
                confidence=0.0,
                video_id="",
                frame_count=0,
                analysis_success=False,
                error_message=error_msg
            )
            
            return result
    
    async def ask_multiple_questions(self, 
                                   questions: List[str],
                                   top_k: int = 20,
                                   min_similarity: float = 0.2,
                                   temporal_weight: float = 0.1,
                                   max_age_seconds: Optional[float] = None) -> List[QueryResult]:
        """Ask multiple questions about the recorded video content via API concurrently
        
        Args:
            questions: List of questions to ask
            top_k: Maximum number of frames to consider per question
            min_similarity: Minimum similarity threshold for frame selection
            temporal_weight: Weight for temporal recency
            max_age_seconds: Only consider frames from last N seconds
            
        Returns:
            List of QueryResult objects, one for each question
        """
        
        session_info = f" (session: {self.session_id})" if self.session_id else ""
        print(f"🤖 Asking {len(questions)} questions concurrently{session_info}...")
        print("=" * 50)
        
        # Create tasks for all questions to run concurrently
        tasks = []
        for question in questions:
            task = self.ask_question(
                question=question,
                top_k=top_k,
                min_similarity=min_similarity,
                temporal_weight=temporal_weight,
                max_age_seconds=max_age_seconds
            )
            tasks.append(task)
        
        # Execute all questions concurrently
        print(f"🚀 Launching {len(questions)} concurrent API requests...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle any exceptions
        processed_results = []
        successful_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle exception from concurrent task
                print(f"❌ Question {i+1} failed with exception: {result}")
                error_result = QueryResult(
                    session_id=self.session_id or "all_sessions",
                    question=questions[i],
                    answer="Unable to analyze the video content due to an error.",
                    confidence=0.0,
                    video_id="",
                    frame_count=0,
                    analysis_success=False,
                    error_message=str(result)
                )
                processed_results.append(error_result)
            else:
                # Normal result
                processed_results.append(result)
                if result.analysis_success:
                    successful_count += 1
                    print(f"✅ Question {i+1} completed successfully")
                    print(f"   Confidence: {result.confidence:.3f}")
                else:
                    print(f"❌ Question {i+1} failed: {result.error_message}")
        
        print(f"\n✅ Completed {len(questions)} questions concurrently")
        print(f"   Successful: {successful_count}")
        print(f"   Failed: {len(questions) - successful_count}")
        
        return processed_results
    
    def get_stats(self) -> QueryStats:
        """Get current query statistics"""
        return self.query_stats
    
    def get_vector_search_stats(self) -> Dict[str, Any]:
        """Get vector search statistics (API-based)"""
        # Since we're using API, we don't have direct access to vector search stats
        # Return basic stats from our tracking
        return {
            "total_searches": self.query_stats.total_search_operations,
            "successful_searches": self.query_stats.successful_queries,
            "failed_searches": self.query_stats.failed_queries,
            "average_confidence": self.query_stats.average_confidence
        }
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get video analysis statistics (API-based)"""
        # Since we're using API, we don't have direct access to analysis stats
        # Return basic stats from our tracking
        return {
            "total_analyses": self.query_stats.total_analysis_operations,
            "successful_analyses": self.query_stats.successful_queries,
            "failed_analyses": self.query_stats.failed_queries,
            "average_confidence": self.query_stats.average_confidence
        }
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        session_info = f" for session: {self.session_id}" if self.session_id else ""
        print(f"🧹 Cleaning up querier{session_info}...")
        
        # No cleanup needed for API-based querier
        print("✅ Querier cleanup completed")


# Factory function for easy creation
def create_querier(session_id: Optional[str] = None) -> Querier:
    """Create a querier for asking questions about video content
    
    Args:
        session_id: Session identifier to query (if None, queries all sessions)
        
    Returns:
        Querier instance
    """
    return Querier(session_id=session_id) 