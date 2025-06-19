"""
Natural Language Understanding Service
Provides intent recognition and entity extraction for better agent task routing
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(Enum):
    """Supported intent types for agent tasks"""
    CODE_DEVELOPMENT = "code_development"
    BUG_FIXING = "bug_fixing"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PLANNING = "planning"
    DESIGN = "design"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"
    REFACTORING = "refactoring"
    OPTIMIZATION = "optimization"
    GENERAL_ASSISTANCE = "general_assistance"


class EntityType(Enum):
    """Entity types that can be extracted"""
    FILE_PATH = "file_path"
    FUNCTION_NAME = "function_name"
    CLASS_NAME = "class_name"
    TECHNOLOGY = "technology"
    ERROR_TYPE = "error_type"
    FEATURE_NAME = "feature_name"
    FRAMEWORK = "framework"
    LANGUAGE = "language"


@dataclass
class Entity:
    """Represents an extracted entity"""
    type: EntityType
    value: str
    confidence: float = 1.0
    start_pos: int = -1
    end_pos: int = -1


@dataclass
class IntentResult:
    """Result of intent classification"""
    primary_intent: Intent
    confidence: float
    secondary_intents: List[Tuple[Intent, float]] = None
    
    def __post_init__(self):
        if self.secondary_intents is None:
            self.secondary_intents = []


@dataclass
class NLUResult:
    """Complete NLU analysis result"""
    intent: IntentResult
    entities: List[Entity]
    structured_task: Dict[str, Any]
    original_text: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "intent": {
                "primary": self.intent.primary_intent.value,
                "confidence": self.intent.confidence,
                "secondary": [
                    {"intent": i.value, "confidence": c} 
                    for i, c in self.intent.secondary_intents
                ]
            },
            "entities": [
                {
                    "type": e.type.value,
                    "value": e.value,
                    "confidence": e.confidence,
                    "position": [e.start_pos, e.end_pos]
                }
                for e in self.entities
            ],
            "structured_task": self.structured_task,
            "original_text": self.original_text
        }


class NLUService:
    """Natural Language Understanding service for agent task routing"""
    
    def __init__(self):
        """Initialize NLU service with pattern definitions"""
        self.intent_patterns = self._initialize_intent_patterns()
        self.entity_patterns = self._initialize_entity_patterns()
        self.technology_keywords = self._initialize_technology_keywords()
        
    def _initialize_intent_patterns(self) -> Dict[Intent, List[re.Pattern]]:
        """Initialize regex patterns for intent detection"""
        return {
            Intent.CODE_DEVELOPMENT: [
                re.compile(r'\b(implement|create|build|develop|write|add)\b.*\b(feature|function|module|component|api|endpoint)\b', re.I),
                re.compile(r'\b(code|program|script)\b.*\b(new|create|implement)\b', re.I),
            ],
            Intent.BUG_FIXING: [
                re.compile(r'\b(fix|resolve|debug|troubleshoot|solve)\b.*\b(bug|issue|error|problem|crash)\b', re.I),
                re.compile(r'\b(bug|error|exception|crash|fault)\b.*\b(fix|resolve|handle)\b', re.I),
                re.compile(r'\bnot working\b|\bbroken\b|\bfailing\b', re.I),
            ],
            Intent.CODE_REVIEW: [
                re.compile(r'\b(review|check|examine|inspect|analyze)\b.*\b(code|implementation|pr|pull request)\b', re.I),
                re.compile(r'\bcode review\b|\bpeer review\b', re.I),
            ],
            Intent.TESTING: [
                re.compile(r'\b(test|verify|validate|check)\b.*\b(functionality|feature|implementation)\b', re.I),
                re.compile(r'\b(write|create|add)\b.*\b(test|tests|unit test|integration test)\b', re.I),
                re.compile(r'\bqa\b|\bquality assurance\b', re.I),
            ],
            Intent.DOCUMENTATION: [
                re.compile(r'\b(document|write|create|update)\b.*\b(documentation|docs|readme|guide)\b', re.I),
                re.compile(r'\b(add|write)\b.*\b(comments|docstring|documentation)\b', re.I),
            ],
            Intent.PLANNING: [
                re.compile(r'\b(plan|design|architect|structure|organize)\b.*\b(project|feature|system|application)\b', re.I),
                re.compile(r'\b(roadmap|timeline|milestone|sprint)\b', re.I),
            ],
            Intent.REFACTORING: [
                re.compile(r'\b(refactor|restructure|reorganize|clean up|improve)\b.*\b(code|implementation|structure)\b', re.I),
                re.compile(r'\b(optimize|enhance|improve)\b.*\b(performance|efficiency|code quality)\b', re.I),
            ],
            Intent.DEPLOYMENT: [
                re.compile(r'\b(deploy|release|publish|launch)\b.*\b(application|service|feature|update)\b', re.I),
                re.compile(r'\b(ci/cd|continuous|pipeline|docker|kubernetes)\b', re.I),
            ],
            Intent.ANALYSIS: [
                re.compile(r'\b(analyze|examine|investigate|study)\b.*\b(code|data|performance|metrics)\b', re.I),
                re.compile(r'\b(profile|benchmark|measure)\b', re.I),
            ],
        }
    
    def _initialize_entity_patterns(self) -> Dict[EntityType, List[re.Pattern]]:
        """Initialize regex patterns for entity extraction"""
        return {
            EntityType.FILE_PATH: [
                re.compile(r'([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)'),
                re.compile(r'`([^`]+\.[a-zA-Z]+)`'),
            ],
            EntityType.FUNCTION_NAME: [
                re.compile(r'\bfunction\s+(\w+)\b', re.I),
                re.compile(r'\bdef\s+(\w+)\b'),
                re.compile(r'(\w+)\(\)'),
            ],
            EntityType.CLASS_NAME: [
                re.compile(r'\bclass\s+(\w+)\b', re.I),
                re.compile(r'\b([A-Z][a-zA-Z0-9]+)(?:\s+class|\s+component)'),
            ],
            EntityType.ERROR_TYPE: [
                re.compile(r'\b(\w+Error)\b'),
                re.compile(r'\b(\w+Exception)\b'),
                re.compile(r'\berror:\s*([^\n]+)', re.I),
            ],
            EntityType.FEATURE_NAME: [
                re.compile(r'"([^"]+)"\s+feature', re.I),
                re.compile(r'feature\s+"([^"]+)"', re.I),
                re.compile(r'`([^`]+)`\s+feature', re.I),
            ],
        }
    
    def _initialize_technology_keywords(self) -> Dict[str, List[str]]:
        """Initialize technology/framework keywords"""
        return {
            "python": ["python", "py", "django", "flask", "fastapi", "pandas", "numpy"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular", "typescript"],
            "java": ["java", "spring", "maven", "gradle", "junit"],
            "go": ["go", "golang", "gin", "gorilla"],
            "rust": ["rust", "cargo", "tokio"],
            "database": ["sql", "postgresql", "mysql", "mongodb", "redis", "database", "db"],
            "cloud": ["aws", "azure", "gcp", "cloud", "kubernetes", "docker", "k8s"],
            "frontend": ["frontend", "ui", "ux", "css", "html", "react", "vue", "angular"],
            "backend": ["backend", "api", "server", "microservice", "rest", "graphql"],
            "mobile": ["ios", "android", "swift", "kotlin", "react native", "flutter"],
        }
    
    def analyze(self, text: str) -> NLUResult:
        """
        Analyze text to extract intent and entities
        
        Args:
            text: Input text to analyze
            
        Returns:
            NLUResult containing intent, entities, and structured task
        """
        # Classify intent
        intent_result = self._classify_intent(text)
        
        # Extract entities
        entities = self._extract_entities(text)
        
        # Extract technologies
        technologies = self._extract_technologies(text)
        
        # Build structured task
        structured_task = self._build_structured_task(
            text, intent_result, entities, technologies
        )
        
        return NLUResult(
            intent=intent_result,
            entities=entities,
            structured_task=structured_task,
            original_text=text
        )
    
    def _classify_intent(self, text: str) -> IntentResult:
        """Classify the intent of the text"""
        intent_scores = {}
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                if pattern.search(text):
                    score += 1.0
            if score > 0:
                intent_scores[intent] = score / len(patterns)
        
        # If no specific intent found, use general assistance
        if not intent_scores:
            return IntentResult(
                primary_intent=Intent.GENERAL_ASSISTANCE,
                confidence=0.5
            )
        
        # Sort by score
        sorted_intents = sorted(
            intent_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Primary intent
        primary_intent, primary_score = sorted_intents[0]
        
        # Secondary intents (if any)
        secondary_intents = [
            (intent, score) 
            for intent, score in sorted_intents[1:3]
            if score > 0.3
        ]
        
        return IntentResult(
            primary_intent=primary_intent,
            confidence=min(primary_score, 0.9),
            secondary_intents=secondary_intents
        )
    
    def _extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text"""
        entities = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    value = match.group(1) if match.groups() else match.group(0)
                    entities.append(Entity(
                        type=entity_type,
                        value=value,
                        confidence=0.8,
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
        
        return entities
    
    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology keywords from text"""
        text_lower = text.lower()
        found_technologies = []
        
        for tech_category, keywords in self.technology_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_technologies.append(keyword)
        
        return list(set(found_technologies))
    
    def _build_structured_task(
        self, 
        text: str, 
        intent: IntentResult, 
        entities: List[Entity],
        technologies: List[str]
    ) -> Dict[str, Any]:
        """Build structured task representation"""
        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            if entity.type not in entities_by_type:
                entities_by_type[entity.type] = []
            entities_by_type[entity.type].append(entity.value)
        
        # Determine recommended agents based on intent
        recommended_agents = self._get_recommended_agents(intent.primary_intent)
        
        # Build task structure
        return {
            "task_type": intent.primary_intent.value,
            "description": text,
            "intent_confidence": intent.confidence,
            "recommended_agents": recommended_agents,
            "entities": {
                entity_type.value: values
                for entity_type, values in entities_by_type.items()
            },
            "technologies": technologies,
            "context": {
                "has_file_references": EntityType.FILE_PATH in entities_by_type,
                "has_error_context": EntityType.ERROR_TYPE in entities_by_type,
                "is_technical": len(technologies) > 0,
                "complexity": self._estimate_complexity(text, entities, technologies)
            },
            "routing_hints": self._generate_routing_hints(
                intent, entities_by_type, technologies
            )
        }
    
    def _get_recommended_agents(self, intent: Intent) -> List[str]:
        """Get recommended agents based on intent"""
        intent_to_agents = {
            Intent.CODE_DEVELOPMENT: ["coding_01", "product_01"],
            Intent.BUG_FIXING: ["bug_01", "coding_01"],
            Intent.CODE_REVIEW: ["coding_01", "product_01", "bug_01"],
            Intent.TESTING: ["bug_01", "coding_01"],
            Intent.DOCUMENTATION: ["product_01", "coding_01"],
            Intent.PLANNING: ["product_01"],
            Intent.DESIGN: ["product_01", "coding_01"],
            Intent.DEPLOYMENT: ["coding_01", "product_01"],
            Intent.ANALYSIS: ["bug_01", "product_01"],
            Intent.REFACTORING: ["coding_01", "bug_01"],
            Intent.OPTIMIZATION: ["coding_01", "bug_01"],
            Intent.GENERAL_ASSISTANCE: ["general_01", "product_01"],
        }
        return intent_to_agents.get(intent, ["general_01"])
    
    def _estimate_complexity(
        self, 
        text: str, 
        entities: List[Entity],
        technologies: List[str]
    ) -> str:
        """Estimate task complexity"""
        # Simple heuristic based on text length, entities, and technologies
        score = 0
        
        # Text length
        word_count = len(text.split())
        if word_count > 100:
            score += 2
        elif word_count > 50:
            score += 1
        
        # Entity count
        if len(entities) > 5:
            score += 2
        elif len(entities) > 2:
            score += 1
        
        # Technology diversity
        if len(technologies) > 3:
            score += 2
        elif len(technologies) > 1:
            score += 1
        
        # Complexity levels
        if score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"
    
    def _generate_routing_hints(
        self,
        intent: IntentResult,
        entities_by_type: Dict[EntityType, List[str]],
        technologies: List[str]
    ) -> Dict[str, Any]:
        """Generate hints for task routing"""
        hints = {
            "requires_file_access": EntityType.FILE_PATH in entities_by_type,
            "requires_debugging": intent.primary_intent == Intent.BUG_FIXING,
            "requires_creativity": intent.primary_intent in [
                Intent.PLANNING, Intent.DESIGN, Intent.DOCUMENTATION
            ],
            "requires_analysis": intent.primary_intent in [
                Intent.ANALYSIS, Intent.CODE_REVIEW, Intent.OPTIMIZATION
            ],
            "is_urgent": any(
                keyword in technologies 
                for keyword in ["error", "bug", "crash", "critical"]
            ),
            "suggested_workflow": self._suggest_workflow(intent.primary_intent)
        }
        return hints
    
    def _suggest_workflow(self, intent: Intent) -> str:
        """Suggest workflow based on intent"""
        workflows = {
            Intent.BUG_FIXING: "analyze_diagnose_fix_test",
            Intent.CODE_DEVELOPMENT: "plan_implement_test_review",
            Intent.CODE_REVIEW: "analyze_feedback_iterate",
            Intent.TESTING: "design_implement_execute_report",
            Intent.REFACTORING: "analyze_plan_implement_validate",
            Intent.DOCUMENTATION: "outline_write_review_publish",
        }
        return workflows.get(intent, "standard")


# Singleton instance
nlu_service = NLUService()


def analyze_task(text: str) -> Dict[str, Any]:
    """
    Convenience function to analyze task text
    
    Args:
        text: Task description text
        
    Returns:
        Dictionary containing NLU analysis results
    """
    result = nlu_service.analyze(text)
    return result.to_dict()