"""
Explainability Engine - Generates human-readable explanations of agent actions
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import re

from services.auditing.agent_auditor import AuditRecord, AuditLevel
from services.auditing.audit_storage import AuditStorage
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ExplainabilityEngine:
    """Generates explainable reports from audit trails"""
    
    def __init__(self, audit_storage: Optional[AuditStorage] = None):
        self.audit_storage = audit_storage
        self.logger = get_logger(__name__)
    
    async def generate_task_explanation(self, task_id: str) -> Dict[str, Any]:
        """Generate a comprehensive explanation for a task"""
        if not self.audit_storage:
            return {"error": "No audit storage configured"}
        
        # Get all audit records for the task
        audit_records = await self.audit_storage.get_records_by_task(task_id)
        
        if not audit_records:
            return {"error": f"No audit records found for task {task_id}"}
        
        # Build the explanation
        explanation = {
            "task_id": task_id,
            "summary": self._generate_summary(audit_records),
            "timeline": self._generate_timeline(audit_records),
            "agent_contributions": self._analyze_agent_contributions(audit_records),
            "decision_flow": self._trace_decision_flow(audit_records),
            "tools_analysis": self._analyze_tool_usage(audit_records),
            "performance_metrics": self._calculate_performance_metrics(audit_records),
            "error_analysis": self._analyze_errors(audit_records),
            "reasoning_chain": self._extract_reasoning_chain(audit_records),
            "recommendations": self._generate_recommendations(audit_records)
        }
        
        return explanation
    
    def _generate_summary(self, records: List[AuditRecord]) -> Dict[str, Any]:
        """Generate a high-level summary of the task"""
        if not records:
            return {}
        
        start_time = min(r.timestamp for r in records)
        end_time = max(r.timestamp for r in records)
        duration = (end_time - start_time).total_seconds()
        
        # Count successes and failures
        successful_actions = sum(1 for r in records if r.success)
        failed_actions = len(records) - successful_actions
        
        # Get unique agents
        agents_involved = list(set(r.agent_name for r in records))
        
        # Total tokens and model calls
        total_tokens = sum(r.tokens_used or 0 for r in records)
        total_model_calls = sum(r.model_calls for r in records)
        
        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_actions": len(records),
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "success_rate": (successful_actions / len(records) * 100) if records else 0,
            "agents_involved": agents_involved,
            "total_tokens_used": total_tokens,
            "total_model_calls": total_model_calls,
            "avg_action_duration_ms": sum(r.duration_ms for r in records) / len(records) if records else 0
        }
    
    def _generate_timeline(self, records: List[AuditRecord]) -> List[Dict[str, Any]]:
        """Generate a timeline of actions"""
        timeline = []
        
        for record in sorted(records, key=lambda r: r.timestamp):
            event = {
                "timestamp": record.timestamp.isoformat(),
                "agent": record.agent_name,
                "action": record.action_name,
                "type": record.action_type,
                "duration_ms": record.duration_ms,
                "success": record.success
            }
            
            # Add key details based on action type
            if record.error_message:
                event["error"] = record.error_message
            
            if record.reasoning:
                event["reasoning"] = record.reasoning[:200] + "..." if len(record.reasoning) > 200 else record.reasoning
            
            if record.tools_used:
                event["tools"] = [tool["tool_name"] for tool in record.tools_used]
            
            timeline.append(event)
        
        return timeline
    
    def _analyze_agent_contributions(self, records: List[AuditRecord]) -> Dict[str, Any]:
        """Analyze what each agent contributed"""
        contributions = defaultdict(lambda: {
            "actions_count": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "total_duration_ms": 0,
            "tools_used": set(),
            "action_types": defaultdict(int),
            "key_outputs": []
        })
        
        for record in records:
            agent_data = contributions[record.agent_name]
            agent_data["actions_count"] += 1
            
            if record.success:
                agent_data["successful_actions"] += 1
            else:
                agent_data["failed_actions"] += 1
            
            agent_data["total_duration_ms"] += record.duration_ms
            agent_data["action_types"][record.action_type] += 1
            
            # Track tools used
            for tool in record.tools_used:
                agent_data["tools_used"].add(tool["tool_name"])
            
            # Extract key outputs
            if record.outputs and record.level in [AuditLevel.STANDARD, AuditLevel.DETAILED]:
                output_summary = self._summarize_output(record.outputs)
                if output_summary:
                    agent_data["key_outputs"].append({
                        "action": record.action_name,
                        "summary": output_summary
                    })
        
        # Convert sets to lists for JSON serialization
        for agent, data in contributions.items():
            data["tools_used"] = list(data["tools_used"])
            data["action_types"] = dict(data["action_types"])
            data["avg_duration_ms"] = data["total_duration_ms"] / data["actions_count"] if data["actions_count"] > 0 else 0
        
        return dict(contributions)
    
    def _trace_decision_flow(self, records: List[AuditRecord]) -> List[Dict[str, Any]]:
        """Trace the flow of decisions through the task"""
        decision_flow = []
        
        for i, record in enumerate(sorted(records, key=lambda r: r.timestamp)):
            if record.reasoning or record.intermediate_steps:
                decision = {
                    "step": i + 1,
                    "agent": record.agent_name,
                    "action": record.action_name,
                    "timestamp": record.timestamp.isoformat(),
                    "reasoning": record.reasoning,
                    "inputs_summary": self._summarize_inputs(record.inputs),
                    "decision_factors": []
                }
                
                # Extract decision factors from intermediate steps
                for step in record.intermediate_steps:
                    if "decision" in step.get("step_name", "").lower():
                        decision["decision_factors"].append(step["data"])
                
                # Look for decision keywords in reasoning
                if record.reasoning:
                    decisions = self._extract_decisions_from_text(record.reasoning)
                    decision["key_decisions"] = decisions
                
                decision_flow.append(decision)
        
        return decision_flow
    
    def _analyze_tool_usage(self, records: List[AuditRecord]) -> Dict[str, Any]:
        """Analyze how tools were used"""
        tool_usage = defaultdict(lambda: {
            "usage_count": 0,
            "agents_using": set(),
            "typical_inputs": [],
            "typical_outputs": [],
            "success_rate": 0,
            "successful_uses": 0
        })
        
        for record in records:
            for tool in record.tools_used:
                tool_name = tool["tool_name"]
                tool_data = tool_usage[tool_name]
                
                tool_data["usage_count"] += 1
                tool_data["agents_using"].add(record.agent_name)
                
                # Track success (assuming tool succeeded if action succeeded)
                if record.success:
                    tool_data["successful_uses"] += 1
                
                # Sample inputs/outputs
                if len(tool_data["typical_inputs"]) < 3:
                    tool_data["typical_inputs"].append(tool.get("input", ""))
                if len(tool_data["typical_outputs"]) < 3:
                    tool_data["typical_outputs"].append(tool.get("output", ""))
        
        # Calculate success rates and convert sets
        for tool_name, data in tool_usage.items():
            data["agents_using"] = list(data["agents_using"])
            data["success_rate"] = (data["successful_uses"] / data["usage_count"] * 100) if data["usage_count"] > 0 else 0
        
        return dict(tool_usage)
    
    def _calculate_performance_metrics(self, records: List[AuditRecord]) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not records:
            return {}
        
        # Time-based metrics
        durations = [r.duration_ms for r in records]
        
        # Token usage
        token_records = [r for r in records if r.tokens_used is not None]
        token_usage = [r.tokens_used for r in token_records] if token_records else []
        
        # Memory usage
        memory_records = [r for r in records if r.memory_used_mb is not None]
        memory_usage = [r.memory_used_mb for r in memory_records] if memory_records else []
        
        return {
            "timing": {
                "total_duration_ms": sum(durations),
                "avg_action_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_action_duration_ms": min(durations) if durations else 0,
                "max_action_duration_ms": max(durations) if durations else 0
            },
            "tokens": {
                "total_tokens": sum(token_usage),
                "avg_tokens_per_action": sum(token_usage) / len(token_usage) if token_usage else 0,
                "actions_with_token_data": len(token_records)
            } if token_usage else None,
            "memory": {
                "avg_memory_mb": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                "peak_memory_mb": max(memory_usage) if memory_usage else 0,
                "actions_with_memory_data": len(memory_records)
            } if memory_usage else None,
            "efficiency": {
                "actions_per_minute": len(records) / (sum(durations) / 60000) if durations else 0,
                "parallel_execution_detected": self._detect_parallel_execution(records)
            }
        }
    
    def _analyze_errors(self, records: List[AuditRecord]) -> Dict[str, Any]:
        """Analyze errors that occurred"""
        error_records = [r for r in records if not r.success]
        
        if not error_records:
            return {"no_errors": True, "error_count": 0}
        
        # Group errors by type
        error_types = defaultdict(list)
        for record in error_records:
            error_type = self._classify_error(record.error_message)
            error_types[error_type].append({
                "agent": record.agent_name,
                "action": record.action_name,
                "timestamp": record.timestamp.isoformat(),
                "message": record.error_message,
                "has_traceback": bool(record.error_traceback)
            })
        
        return {
            "error_count": len(error_records),
            "error_rate": (len(error_records) / len(records) * 100) if records else 0,
            "errors_by_type": dict(error_types),
            "agents_with_errors": list(set(r.agent_name for r in error_records)),
            "error_timeline": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "agent": r.agent_name,
                    "action": r.action_name,
                    "error": r.error_message[:100] + "..." if len(r.error_message or "") > 100 else r.error_message
                }
                for r in sorted(error_records, key=lambda x: x.timestamp)
            ]
        }
    
    def _extract_reasoning_chain(self, records: List[AuditRecord]) -> List[Dict[str, Any]]:
        """Extract the chain of reasoning across agents"""
        reasoning_chain = []
        
        for record in sorted(records, key=lambda r: r.timestamp):
            if record.reasoning:
                # Look for references to other agents or previous steps
                references = self._find_cross_references(record.reasoning, records)
                
                reasoning_chain.append({
                    "agent": record.agent_name,
                    "action": record.action_name,
                    "timestamp": record.timestamp.isoformat(),
                    "reasoning": record.reasoning,
                    "references_previous_steps": references,
                    "builds_on": self._find_dependencies(record, records)
                })
        
        return reasoning_chain
    
    def _generate_recommendations(self, records: List[AuditRecord]) -> List[str]:
        """Generate recommendations based on the audit trail"""
        recommendations = []
        
        # Check for performance issues
        slow_actions = [r for r in records if r.duration_ms > 5000]  # Actions taking > 5 seconds
        if slow_actions:
            recommendations.append(
                f"Performance: {len(slow_actions)} actions took over 5 seconds. "
                f"Consider optimizing {', '.join(set(a.action_name for a in slow_actions[:3]))}"
            )
        
        # Check for high error rates
        error_rate = sum(1 for r in records if not r.success) / len(records) * 100 if records else 0
        if error_rate > 10:
            recommendations.append(
                f"Reliability: Error rate is {error_rate:.1f}%. "
                "Review error handling and add retries for common failures."
            )
        
        # Check for token usage
        high_token_actions = [r for r in records if r.tokens_used and r.tokens_used > 1000]
        if high_token_actions:
            recommendations.append(
                f"Cost: {len(high_token_actions)} actions used over 1000 tokens. "
                "Consider prompt optimization or caching for repeated queries."
            )
        
        # Check for sequential bottlenecks
        if not self._detect_parallel_execution(records) and len(records) > 10:
            recommendations.append(
                "Parallelization: All actions appear sequential. "
                "Consider parallel execution for independent tasks."
            )
        
        # Check for repeated tool usage
        tool_usage = defaultdict(int)
        for record in records:
            for tool in record.tools_used:
                tool_usage[tool["tool_name"]] += 1
        
        frequently_used_tools = [tool for tool, count in tool_usage.items() if count > 5]
        if frequently_used_tools:
            recommendations.append(
                f"Tool Optimization: Tools {', '.join(frequently_used_tools[:3])} are frequently used. "
                "Consider batch operations or caching results."
            )
        
        return recommendations
    
    # Helper methods
    
    def _summarize_output(self, outputs: Dict[str, Any]) -> Optional[str]:
        """Create a summary of outputs"""
        if not outputs:
            return None
        
        # Extract key information
        result = outputs.get("result", "")
        result_type = outputs.get("type", "")
        
        if isinstance(result, str) and len(result) > 100:
            return f"{result_type}: {result[:100]}..."
        elif isinstance(result, (list, dict)):
            return f"{result_type}: {len(result)} items"
        else:
            return f"{result_type}: {result}"
    
    def _summarize_inputs(self, inputs: Dict[str, Any]) -> str:
        """Create a summary of inputs"""
        if not inputs:
            return "No inputs"
        
        # Summarize args and kwargs
        args = inputs.get("args", "")
        kwargs = inputs.get("kwargs", "")
        
        summary_parts = []
        if args and args != "()":
            summary_parts.append(f"args: {args[:50]}...")
        if kwargs and kwargs != "{}":
            summary_parts.append(f"kwargs: {kwargs[:50]}...")
        
        return " | ".join(summary_parts) if summary_parts else "Empty inputs"
    
    def _extract_decisions_from_text(self, text: str) -> List[str]:
        """Extract decision points from reasoning text"""
        decisions = []
        
        # Look for decision keywords
        decision_patterns = [
            r"decided to (.+?)(?:\.|,|;|$)",
            r"choosing (.+?)(?:\.|,|;|$)",
            r"selected (.+?)(?:\.|,|;|$)",
            r"determined that (.+?)(?:\.|,|;|$)",
            r"concluded (.+?)(?:\.|,|;|$)"
        ]
        
        for pattern in decision_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            decisions.extend(matches)
        
        return decisions[:5]  # Limit to top 5 decisions
    
    def _classify_error(self, error_message: Optional[str]) -> str:
        """Classify error types"""
        if not error_message:
            return "unknown"
        
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "network"
        elif "permission" in error_lower or "access" in error_lower:
            return "permission"
        elif "not found" in error_lower or "404" in error_lower:
            return "not_found"
        elif "rate limit" in error_lower:
            return "rate_limit"
        elif "memory" in error_lower:
            return "memory"
        elif "invalid" in error_lower or "validation" in error_lower:
            return "validation"
        else:
            return "other"
    
    def _detect_parallel_execution(self, records: List[AuditRecord]) -> bool:
        """Detect if actions were executed in parallel"""
        if len(records) < 2:
            return False
        
        # Sort by start time
        sorted_records = sorted(records, key=lambda r: r.timestamp)
        
        # Check for overlapping execution times
        for i in range(len(sorted_records) - 1):
            current = sorted_records[i]
            next_record = sorted_records[i + 1]
            
            # Calculate end time of current record
            current_end = current.timestamp + timedelta(milliseconds=current.duration_ms)
            
            # If next record started before current ended, we have parallel execution
            if next_record.timestamp < current_end:
                return True
        
        return False
    
    def _find_cross_references(self, text: str, all_records: List[AuditRecord]) -> List[str]:
        """Find references to other agents or actions in reasoning text"""
        references = []
        
        # Get all agent names
        agent_names = set(r.agent_name for r in all_records)
        
        for agent in agent_names:
            if agent.lower() in text.lower() and agent != "General Assistant":
                references.append(f"References {agent}")
        
        # Look for action references
        action_patterns = ["based on", "following", "as mentioned", "referring to"]
        for pattern in action_patterns:
            if pattern in text.lower():
                references.append(f"References previous action ({pattern})")
                break
        
        return references
    
    def _find_dependencies(self, record: AuditRecord, all_records: List[AuditRecord]) -> List[str]:
        """Find what previous actions this record depends on"""
        dependencies = []
        
        # Look at records before this one
        previous_records = [r for r in all_records if r.timestamp < record.timestamp]
        
        # Check if this record uses outputs from previous records
        if record.inputs:
            input_str = str(record.inputs)
            for prev in previous_records[-5:]:  # Check last 5 records
                if prev.outputs:
                    # Simple check if previous output appears in current input
                    output_str = str(prev.outputs.get("result", ""))[:50]
                    if output_str and output_str in input_str:
                        dependencies.append(f"{prev.agent_name}'s {prev.action_name}")
        
        return dependencies