"""
Zen MCP Service Integration
Provides multi-model AI orchestration and advanced development tools
"""

import os
import logging
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ZenMCPService:
    """Service for integrating Zen MCP Server capabilities"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv('ZEN_MCP_URL', 'http://localhost:3000')
        self.enabled = os.getenv('ZEN_MCP_ENABLED', 'false').lower() == 'true'
        self.client = httpx.AsyncClient(timeout=60.0)
        
        if not self.enabled:
            logger.info("Zen MCP Service is disabled")
        else:
            logger.info(f"Zen MCP Service initialized with URL: {self.base_url}")
    
    async def is_available(self) -> bool:
        """Check if Zen MCP Server is available"""
        if not self.enabled:
            return False
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Zen MCP Server not available: {e}")
            return False
    
    async def chat(self, message: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Use Zen's collaborative thinking tool"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "chat",
                "message": message,
                "context": context
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Zen chat failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error calling Zen chat: {e}")
            return {"error": str(e)}
    
    async def think_deep(self, problem: str, constraints: Optional[List[str]] = None) -> Dict[str, Any]:
        """Use Zen's extended reasoning tool for complex problems"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "thinkdeep",
                "problem": problem,
                "constraints": constraints or []
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Zen think deep failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error calling Zen think deep: {e}")
            return {"error": str(e)}
    
    async def code_review(self, code_path: str, focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Use Zen's professional code review tool"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "codereview",
                "path": code_path,
                "focus": focus_areas or ["best practices", "bugs", "performance", "security"]
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Code review completed for {code_path}")
                return result
            else:
                return {"error": f"Code review failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error in code review: {e}")
            return {"error": str(e)}
    
    async def debug(self, error_message: str, code_context: str, stack_trace: Optional[str] = None) -> Dict[str, Any]:
        """Use Zen's debugging tool for root cause analysis"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "debug",
                "error": error_message,
                "context": code_context,
                "stackTrace": stack_trace
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Debug analysis failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error in debug analysis: {e}")
            return {"error": str(e)}
    
    async def planner(self, project_description: str, requirements: List[str], constraints: Optional[List[str]] = None) -> Dict[str, Any]:
        """Use Zen's step-by-step project planning tool"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "planner",
                "project": project_description,
                "requirements": requirements,
                "constraints": constraints or []
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Planning failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error in project planning: {e}")
            return {"error": str(e)}
    
    async def consensus(self, question: str, perspectives: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use Zen's multi-model consensus tool"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "consensus",
                "question": question,
                "perspectives": perspectives
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Consensus building failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error building consensus: {e}")
            return {"error": str(e)}
    
    async def refactor(self, code_path: str, target_improvements: List[str]) -> Dict[str, Any]:
        """Use Zen's intelligent code refactoring tool"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "refactor",
                "path": code_path,
                "improvements": target_improvements
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Refactoring failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error in refactoring: {e}")
            return {"error": str(e)}
    
    async def analyze(self, code_path: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Use Zen's code analysis tool"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "analyze",
                "path": code_path,
                "type": analysis_type
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Analysis failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error in code analysis: {e}")
            return {"error": str(e)}
    
    async def tracer(self, entry_point: str, target_function: str) -> Dict[str, Any]:
        """Use Zen's call-flow mapping tool"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            payload = {
                "tool": "tracer",
                "entry": entry_point,
                "target": target_function
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/tool",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Tracing failed: {response.text}"}
                
        except Exception as e:
            logger.error(f"Error in call-flow tracing: {e}")
            return {"error": str(e)}
    
    async def multi_model_query(self, query: str, models: Optional[List[str]] = None) -> Dict[str, Any]:
        """Query multiple AI models and get consolidated response"""
        try:
            if not self.enabled:
                return {"error": "Zen MCP is not enabled"}
            
            # First get individual perspectives
            perspectives = []
            
            # Use think deep for complex reasoning
            deep_thought = await self.think_deep(query)
            if 'error' not in deep_thought:
                perspectives.append({
                    "model": "zen-deep-thinking",
                    "response": deep_thought.get('result', '')
                })
            
            # Use chat for conversational response
            chat_response = await self.chat(query)
            if 'error' not in chat_response:
                perspectives.append({
                    "model": "zen-collaborative",
                    "response": chat_response.get('result', '')
                })
            
            # Build consensus if multiple perspectives
            if len(perspectives) > 1:
                consensus = await self.consensus(query, perspectives)
                return {
                    "individual_responses": perspectives,
                    "consensus": consensus.get('result', ''),
                    "confidence": consensus.get('confidence', 0)
                }
            elif len(perspectives) == 1:
                return {
                    "response": perspectives[0]['response'],
                    "model": perspectives[0]['model']
                }
            else:
                return {"error": "No valid responses from models"}
                
        except Exception as e:
            logger.error(f"Error in multi-model query: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Singleton instance
zen_service = None

def get_zen_service() -> ZenMCPService:
    """Get or create the Zen MCP service instance"""
    global zen_service
    if zen_service is None:
        zen_service = ZenMCPService()
    return zen_service