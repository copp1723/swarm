"""
Agent Orchestrator Service
Intelligently routes tasks to appropriate agents using NLU analysis
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from services.nlu_service import nlu_service, Intent
from services.multi_agent_executor import MultiAgentExecutor
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Represents a routing decision for a task"""
    primary_agents: List[str]
    secondary_agents: List[str]
    workflow_type: str
    reasoning: str
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class TaskExecutionPlan:
    """Execution plan for a task"""
    task_id: str
    routing_decision: RoutingDecision
    nlu_analysis: Dict[str, Any]
    execution_steps: List[Dict[str, Any]]
    estimated_duration: int  # seconds
    priority: str
    created_at: datetime


class AgentOrchestrator:
    """Orchestrates task execution across multiple agents"""
    
    def __init__(self, executor: Optional[MultiAgentExecutor] = None):
        """Initialize orchestrator with executor"""
        self.executor = executor or MultiAgentExecutor()
        self.routing_rules = self._initialize_routing_rules()
        self.workflow_templates = self._initialize_workflow_templates()
        
    def _initialize_routing_rules(self) -> Dict[str, Any]:
        """Initialize routing rules for different scenarios"""
        return {
            "complexity_thresholds": {
                "simple": 1,  # Single agent
                "moderate": 2,  # 2-3 agents
                "complex": 4   # 4+ agents
            },
            "intent_priorities": {
                Intent.BUG_FIXING.value: "high",
                Intent.DEPLOYMENT.value: "high",
                Intent.CODE_REVIEW.value: "medium",
                Intent.TESTING.value: "medium",
                Intent.DOCUMENTATION.value: "low",
                Intent.PLANNING.value: "low",
            },
            "agent_capabilities": {
                "coding_01": ["code_development", "refactoring", "optimization", "deployment"],
                "bug_01": ["bug_fixing", "analysis", "testing", "code_review"],
                "product_01": ["planning", "design", "documentation", "general_assistance"],
                "general_01": ["general_assistance", "analysis", "documentation"],
            }
        }
    
    def _initialize_workflow_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize workflow templates for common scenarios"""
        return {
            "bug_fix_workflow": [
                {"step": "analyze", "agent": "bug_01", "action": "diagnose_issue"},
                {"step": "implement", "agent": "coding_01", "action": "fix_code"},
                {"step": "test", "agent": "bug_01", "action": "verify_fix"},
                {"step": "review", "agent": "product_01", "action": "validate_solution"}
            ],
            "feature_development": [
                {"step": "design", "agent": "product_01", "action": "create_specification"},
                {"step": "implement", "agent": "coding_01", "action": "develop_feature"},
                {"step": "test", "agent": "bug_01", "action": "test_feature"},
                {"step": "document", "agent": "product_01", "action": "update_documentation"}
            ],
            "code_review": [
                {"step": "analyze", "agent": "coding_01", "action": "review_code"},
                {"step": "security", "agent": "bug_01", "action": "security_check"},
                {"step": "feedback", "agent": "product_01", "action": "provide_feedback"}
            ],
            "emergency_fix": [
                {"step": "triage", "agent": "bug_01", "action": "assess_severity"},
                {"step": "fix", "agent": "coding_01", "action": "emergency_patch"},
                {"step": "deploy", "agent": "coding_01", "action": "hot_deploy"}
            ]
        }
    
    def analyze_and_route(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> TaskExecutionPlan:
        """
        Analyze task and create execution plan
        
        Args:
            task_description: Natural language task description
            context: Additional context (e.g., working directory, urgency)
            
        Returns:
            TaskExecutionPlan with routing decision and execution steps
        """
        # Analyze with NLU
        nlu_result = nlu_service.analyze(task_description)
        nlu_dict = nlu_result.to_dict()
        
        # Make routing decision
        routing_decision = self._make_routing_decision(nlu_dict, context)
        
        # Create execution plan
        execution_steps = self._create_execution_steps(
            routing_decision, 
            nlu_dict,
            context
        )
        
        # Estimate duration
        estimated_duration = self._estimate_duration(execution_steps, nlu_dict)
        
        # Determine priority
        priority = self._determine_priority(nlu_dict, context)
        
        return TaskExecutionPlan(
            task_id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            routing_decision=routing_decision,
            nlu_analysis=nlu_dict,
            execution_steps=execution_steps,
            estimated_duration=estimated_duration,
            priority=priority,
            created_at=datetime.now()
        )
    
    def _make_routing_decision(self, nlu_analysis: Dict[str, Any], context: Optional[Dict[str, Any]]) -> RoutingDecision:
        """Make routing decision based on NLU analysis"""
        intent = nlu_analysis["intent"]["primary"]
        recommended_agents = nlu_analysis["structured_task"]["recommended_agents"]
        complexity = nlu_analysis["structured_task"]["context"]["complexity"]
        
        # Determine workflow type
        workflow_type = self._select_workflow_type(intent, complexity, context)
        
        # Select agents based on capabilities and availability
        primary_agents = self._select_primary_agents(
            recommended_agents,
            intent,
            complexity
        )
        
        # Select backup agents
        secondary_agents = self._select_secondary_agents(
            primary_agents,
            intent
        )
        
        # Generate reasoning
        reasoning = self._generate_routing_reasoning(
            intent,
            primary_agents,
            complexity,
            nlu_analysis
        )
        
        return RoutingDecision(
            primary_agents=primary_agents,
            secondary_agents=secondary_agents,
            workflow_type=workflow_type,
            reasoning=reasoning,
            confidence=nlu_analysis["intent"]["confidence"],
            metadata={
                "intent": intent,
                "complexity": complexity,
                "has_entities": len(nlu_analysis["structured_task"]["entities"]) > 0,
                "technologies": nlu_analysis["structured_task"]["technologies"]
            }
        )
    
    def _select_workflow_type(self, intent: str, complexity: str, context: Optional[Dict[str, Any]]) -> str:
        """Select appropriate workflow type"""
        # Check for emergency context
        if context and context.get("emergency", False):
            return "emergency_fix"
        
        # Map intent to workflow
        intent_workflow_map = {
            "bug_fixing": "bug_fix_workflow",
            "code_development": "feature_development",
            "code_review": "code_review",
        }
        
        return intent_workflow_map.get(intent, "feature_development")
    
    def _select_primary_agents(self, recommended: List[str], intent: str, complexity: str) -> List[str]:
        """Select primary agents for the task"""
        # For simple tasks, use single agent
        if complexity == "low":
            return recommended[:1]
        
        # For moderate complexity, use 2-3 agents
        elif complexity == "medium":
            return recommended[:3]
        
        # For complex tasks, potentially use all recommended agents
        else:
            # Ensure we have diverse capabilities
            agents = recommended[:4]
            
            # Add specialized agents if needed
            if intent == "bug_fixing" and "bug_01" not in agents:
                agents.append("bug_01")
            elif intent == "planning" and "product_01" not in agents:
                agents.append("product_01")
            
            return agents[:4]  # Cap at 4 agents
    
    def _select_secondary_agents(self, primary: List[str], intent: str) -> List[str]:
        """Select secondary/backup agents"""
        all_agents = ["coding_01", "bug_01", "product_01", "general_01"]
        
        # Secondary agents are those not in primary
        secondary = [a for a in all_agents if a not in primary]
        
        # Prioritize based on intent
        if intent == "bug_fixing":
            secondary.sort(key=lambda x: 0 if x == "coding_01" else 1)
        elif intent == "code_development":
            secondary.sort(key=lambda x: 0 if x == "bug_01" else 1)
        
        return secondary[:2]
    
    def _generate_routing_reasoning(
        self, 
        intent: str, 
        agents: List[str],
        complexity: str,
        nlu_analysis: Dict[str, Any]
    ) -> str:
        """Generate human-readable routing reasoning"""
        agent_names = {
            "coding_01": "Coding Agent",
            "bug_01": "Bug Agent",
            "product_01": "Product Agent",
            "general_01": "General Assistant"
        }
        
        agent_list = ", ".join([agent_names.get(a, a) for a in agents])
        
        reasoning = f"Based on the {intent.replace('_', ' ')} intent "
        reasoning += f"with {complexity} complexity, "
        reasoning += f"I've selected {agent_list} for this task. "
        
        # Add entity context
        entities = nlu_analysis["structured_task"]["entities"]
        if entities:
            entity_types = list(entities.keys())
            reasoning += f"The task involves {', '.join(entity_types)}. "
        
        # Add technology context
        techs = nlu_analysis["structured_task"]["technologies"]
        if techs:
            reasoning += f"Technologies detected: {', '.join(techs[:3])}."
        
        return reasoning
    
    def _create_execution_steps(
        self,
        routing: RoutingDecision,
        nlu_analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create detailed execution steps"""
        workflow_type = routing.workflow_type
        
        # Get base workflow template
        if workflow_type in self.workflow_templates:
            steps = self.workflow_templates[workflow_type].copy()
        else:
            # Create dynamic workflow
            steps = self._create_dynamic_workflow(routing, nlu_analysis)
        
        # Enhance steps with context
        enhanced_steps = []
        for i, step in enumerate(steps):
            enhanced_step = {
                **step,
                "step_number": i + 1,
                "entities": nlu_analysis["structured_task"]["entities"],
                "context": {
                    "working_directory": context.get("working_directory", "./") if context else "./",
                    "technologies": nlu_analysis["structured_task"]["technologies"],
                    "has_file_references": nlu_analysis["structured_task"]["context"]["has_file_references"]
                }
            }
            enhanced_steps.append(enhanced_step)
        
        return enhanced_steps
    
    def _create_dynamic_workflow(
        self,
        routing: RoutingDecision,
        nlu_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create dynamic workflow when no template matches"""
        steps = []
        
        # Always start with analysis
        steps.append({
            "step": "analyze",
            "agent": routing.primary_agents[0],
            "action": "analyze_requirements"
        })
        
        # Add main execution step
        steps.append({
            "step": "execute",
            "agent": routing.primary_agents[0],
            "action": "implement_solution"
        })
        
        # Add verification if multiple agents
        if len(routing.primary_agents) > 1:
            steps.append({
                "step": "verify",
                "agent": routing.primary_agents[1],
                "action": "verify_implementation"
            })
        
        return steps
    
    def _estimate_duration(self, steps: List[Dict[str, Any]], nlu_analysis: Dict[str, Any]) -> int:
        """Estimate task duration in seconds"""
        base_duration = 60  # 1 minute base
        
        # Add time per step
        step_duration = len(steps) * 30
        
        # Adjust for complexity
        complexity = nlu_analysis["structured_task"]["context"]["complexity"]
        complexity_multiplier = {
            "low": 1,
            "medium": 2,
            "high": 3
        }
        
        total_duration = (base_duration + step_duration) * complexity_multiplier.get(complexity, 1)
        
        return int(total_duration)
    
    def _determine_priority(self, nlu_analysis: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
        """Determine task priority"""
        intent = nlu_analysis["intent"]["primary"]
        
        # Check context for explicit priority
        if context and "priority" in context:
            return context["priority"]
        
        # Check routing hints
        hints = nlu_analysis["structured_task"]["routing_hints"]
        if hints.get("is_urgent", False):
            return "high"
        
        # Use intent-based priority
        intent_priority = self.routing_rules["intent_priorities"].get(intent, "medium")
        
        return intent_priority
    
    def execute_plan(self, plan: TaskExecutionPlan, **kwargs) -> Dict[str, Any]:
        """
        Execute a task plan
        
        Args:
            plan: TaskExecutionPlan to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Execution results
        """
        logger.info(f"Executing plan {plan.task_id} with {len(plan.execution_steps)} steps")
        
        # Prepare execution parameters
        task_description = plan.nlu_analysis["original_text"]
        agent_roles = [agent.replace("_01", "") for agent in plan.routing_decision.primary_agents]
        working_directory = kwargs.get("working_directory", "./")
        
        # Add structured task info to description
        enhanced_description = f"{task_description}\n\n[Orchestrator Analysis]\n"
        enhanced_description += f"Intent: {plan.nlu_analysis['intent']['primary']}\n"
        enhanced_description += f"Workflow: {plan.routing_decision.workflow_type}\n"
        enhanced_description += f"Priority: {plan.priority}\n"
        
        # Execute through multi-agent executor
        result = self.executor.execute_collaborative_task(
            task_description=enhanced_description,
            tagged_agents=plan.routing_decision.primary_agents,
            working_directory=working_directory,
            sequential=plan.routing_decision.workflow_type != "emergency_fix",
            enhance_prompt=False  # Already enhanced
        )
        
        # Add orchestration metadata to result
        if result.get("success"):
            result["orchestration"] = {
                "plan_id": plan.task_id,
                "routing_decision": asdict(plan.routing_decision),
                "nlu_analysis": plan.nlu_analysis,
                "execution_steps": plan.execution_steps,
                "estimated_vs_actual": {
                    "estimated_duration": plan.estimated_duration,
                    "actual_duration": result.get("execution_time", 0)
                }
            }
        
        return result


# Singleton instance
orchestrator = AgentOrchestrator()


def orchestrate_task(task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to orchestrate a task
    
    Args:
        task_description: Natural language task description
        context: Optional context information
        
    Returns:
        Execution results with orchestration metadata
    """
    # Create execution plan
    plan = orchestrator.analyze_and_route(task_description, context)
    
    # Execute plan
    result = orchestrator.execute_plan(plan, **(context or {}))
    
    return result