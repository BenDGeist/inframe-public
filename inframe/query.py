#!/usr/bin/env python3

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Callable, Any, Awaitable
from dataclasses import dataclass

from src.context_querier import create_context_querier, QueryResult

@dataclass
class QueryConfig:
    """Configuration for a query"""
    query_id: str
    prompt: str
    callback: Optional[Callable[[QueryResult], Awaitable[None]]]
    recorder: Any  # ContextRecorder
    interval_seconds: float
    recorder_internal_id: Optional[str] = None  # Store the internal recorder ID for tracking

class ContextQuery:
    """Unified query system that monitors recorders and runs prompts on context updates"""
    
    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.openai_api_key = openai_api_key
        self.model = model
        self._id = str(uuid.uuid4())  # Generate unique ID for this instance
        
        # Query storage
        self.queries: Dict[str, QueryConfig] = {}
        self.context_queriers: Dict[str, Any] = {}  # query_id -> ContextQuerier
        
        # State
        self.is_running = False
    
    def __hash__(self):
        """Make ContextQuery hashable using its unique ID"""
        return hash(self._id)
    
    def __eq__(self, other):
        """Check equality based on unique ID"""
        if isinstance(other, ContextQuery):
            return self._id == other._id
        return False
    
    @property
    def id(self):
        """Get the unique ID for this query"""
        return self._id
        
    def add_query(self, prompt: str, recorder, callback: Optional[Callable[[QueryResult], Awaitable[None]]] = None, 
                  interval_seconds: float = 30.0) -> str:
        """Add a query to monitor the recorder with the given prompt"""
        query_id = str(uuid.uuid4())
        
        config = QueryConfig(
            query_id=query_id,
            prompt=prompt,
            callback=callback,
            recorder=recorder,
            interval_seconds=interval_seconds
        )
        
        self.queries[query_id] = config
        print(f"📊 Added query: {prompt[:50]}...")
        return query_id
    
    async def start(self, query_id: Optional[str] = None) -> bool:
        """Start monitoring. If query_id specified, start only that query, otherwise start all"""
        try:
            if query_id:
                if query_id in self.queries:
                    await self._start_query(query_id)
                else:
                    print(f"❌ Query ID {query_id} not found")
                    return False
            else:
                # Start all queries
                for qid in self.queries.keys():
                    await self._start_query(qid)
                self.is_running = True
                
            print(f"🚀 Started query monitoring")
            return True
        except Exception as e:
            print(f"❌ Error starting query: {e}")
            return False
    
    async def stop(self, query_id: Optional[str] = None) -> bool:
        """Stop monitoring. If query_id specified, stop only that query, otherwise stop all"""
        try:
            if query_id:
                await self._stop_query(query_id)
                
            print(f"🛑 Stopped query monitoring")
            return True
        except Exception as e:
            print(f"❌ Error stopping query: {e}")
            return False
    
    async def shutdown(self):
        """Gracefully shutdown all queries"""
        # Stop all queries with proper exception handling
        tasks_to_wait = []
        for query_id in list(self.queries.keys()):
            try:
                await self._stop_query(query_id)
            except Exception as e:
                print(f"❌ Error stopping query {query_id[:8]}: {e}")
        
        self.is_running = False
    
    async def _start_query(self, query_id: str):
        """Start monitoring for a specific query"""
        if query_id not in self.queries:
            raise ValueError(f"Query {query_id} not found")
            
        config = self.queries[query_id]
        
        # Check if recorder is running before starting query
        if not config.recorder.is_recording:
            raise ValueError("Recorder must be running before starting queries")
        
        # Create context querier for this query
        context_querier = create_context_querier(
            openai_api_key=self.openai_api_key,
            model=self.model,
            query_interval_seconds=config.interval_seconds
        )
        
        # Set up callback to handle results
        if config.callback:
            context_querier.set_result_callback(self._create_result_handler(config))
        
        # Start monitoring the recorder
        await context_querier.start_querier(config.recorder.context_integrator, config.prompt)
        
        # Store the querier
        self.context_queriers[query_id] = context_querier
        

    
    async def _stop_query(self, query_id: str):
        """Stop monitoring for a specific query with timeout safety"""
        if query_id in self.context_queriers:
            querier = self.context_queriers[query_id]
            try:
                await asyncio.wait_for(querier.stop_querier(), timeout=3.0)
                print(f"🛑 Stopped query: {query_id[:8]}...")
            except asyncio.TimeoutError:
                print(f"⚠️ Query {query_id[:8]} took too long to stop")
            except asyncio.CancelledError:
                print(f"⚠️ Query {query_id[:8]} was cancelled during shutdown")
            except Exception as e:
                print(f"❌ Error stopping query {query_id[:8]}: {e}")
            finally:
                # Always clean up the reference
                del self.context_queriers[query_id]
    
    def _create_result_handler(self, config: QueryConfig):
        """Create a result handler for the given query config"""
        async def handle_result(result: QueryResult):
            if config.callback:
                try:
                    await config.callback(result)
                except Exception as e:
                    print(f"❌ Error in callback for query {config.query_id[:8]}: {e}")
        
        return handle_result
