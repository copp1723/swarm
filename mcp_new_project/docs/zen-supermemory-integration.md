# Zen MCP & Supermemory Integration Guide

## Overview
This document outlines the integration of two powerful MCP servers into the Multi-Agent Chat System:
1. **Zen MCP Server** - Multi-model AI orchestration and development tools
2. **Supermemory MCP** - Universal memory system for persistent agent knowledge

## 1. Zen MCP Server Integration

### Benefits
- **Multi-Model Intelligence**: Agents can leverage multiple AI models for better responses
- **Advanced Reasoning**: Tools like `thinkdeep` and `consensus` for complex problem-solving
- **Development Tools**: Professional code review, debugging, and refactoring capabilities
- **Flexible Model Selection**: Automatic selection of best model for each task

### Integration Steps

#### Step 1: Update MCP Configuration
Add Zen server to `config/mcp_servers.json`:
```json
{
  "zen": {
    "name": "Zen MCP Server",
    "command": "docker",
    "args": ["run", "-p", "3000:3000", "beehiveinnovations/zen-mcp-server"],
    "env": {
      "GEMINI_API_KEY": "${GEMINI_API_KEY}",
      "OPENAI_API_KEY": "${OPENAI_API_KEY}"
    },
    "capabilities": ["multi_model", "development", "reasoning"]
  }
}
```

#### Step 2: Map Tools to Agents
Update `config/agents.json` to assign Zen tools:
```json
{
  "coder": {
    "tools": ["filesystem", "zen:codereview", "zen:refactor", "zen:analyze"],
    "description": "Enhanced with Zen's code analysis capabilities"
  },
  "bug": {
    "tools": ["filesystem", "zen:debug", "zen:tracer"],
    "description": "Enhanced with Zen's debugging tools"
  },
  "product": {
    "tools": ["filesystem", "zen:planner", "zen:consensus"],
    "description": "Enhanced with Zen's planning and consensus tools"
  }
}
```

#### Step 3: Implement Tool Wrappers
Create wrappers in `services/zen_integration.py`:
```python
class ZenIntegration:
    async def code_review(self, code_path, context):
        """Use Zen's code review tool"""
        return await mcp_manager.call_tool("zen:codereview", {
            "path": code_path,
            "context": context
        })
    
    async def think_deep(self, problem, constraints):
        """Use Zen's deep thinking for complex problems"""
        return await mcp_manager.call_tool("zen:thinkdeep", {
            "problem": problem,
            "constraints": constraints
        })
```

## 2. Supermemory MCP Integration

### Benefits
- **Persistent Memory**: Agents remember past interactions and learned information
- **Shared Knowledge**: All agents can access common memory pool
- **Context Preservation**: Maintain project context across sessions
- **No Authentication**: Free and accessible without login requirements

### Integration Steps

#### Step 1: Add Supermemory Server
Update `config/mcp_servers.json`:
```json
{
  "supermemory": {
    "name": "Supermemory MCP",
    "command": "npx",
    "args": ["-y", "@supermemory/mcp"],
    "env": {
      "SUPERMEMORY_API_KEY": "${SUPERMEMORY_API_KEY}"
    },
    "capabilities": ["memory", "persistence"]
  }
}
```

#### Step 2: Create Memory Service
Implement `services/memory_service.py`:
```python
from typing import Dict, Any, Optional
import json

class AgentMemoryService:
    def __init__(self, mcp_manager):
        self.mcp = mcp_manager
        
    async def remember(self, agent_id: str, key: str, value: Any):
        """Store memory for an agent"""
        memory_key = f"{agent_id}:{key}"
        return await self.mcp.call_tool("supermemory:store", {
            "key": memory_key,
            "value": json.dumps(value),
            "metadata": {
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            }
        })
    
    async def recall(self, agent_id: str, key: str) -> Optional[Any]:
        """Retrieve memory for an agent"""
        memory_key = f"{agent_id}:{key}"
        result = await self.mcp.call_tool("supermemory:retrieve", {
            "key": memory_key
        })
        return json.loads(result) if result else None
    
    async def search_memories(self, query: str, agent_id: Optional[str] = None):
        """Search through memories"""
        filters = {"agent_id": agent_id} if agent_id else {}
        return await self.mcp.call_tool("supermemory:search", {
            "query": query,
            "filters": filters
        })
```

#### Step 3: Enhance Agent Conversations
Update `services/multi_agent_executor.py`:
```python
class EnhancedAgentExecutor:
    def __init__(self):
        self.memory_service = AgentMemoryService(mcp_manager)
        
    async def enhance_with_memory(self, agent_id: str, prompt: str):
        # Search for relevant memories
        memories = await self.memory_service.search_memories(
            query=prompt,
            agent_id=agent_id
        )
        
        if memories:
            context = "Relevant past knowledge:\n"
            for memory in memories[:3]:  # Top 3 relevant memories
                context += f"- {memory['content']}\n"
            
            enhanced_prompt = f"{context}\n\nCurrent task: {prompt}"
            return enhanced_prompt
        
        return prompt
```

## 3. Combined Power: Zen + Supermemory

### Use Case Examples

#### 1. Intelligent Code Review with Memory
```python
async def smart_code_review(file_path, agent_id="coder_01"):
    # Recall previous reviews of similar code
    past_reviews = await memory_service.recall(
        agent_id, 
        f"reviews:{file_path}"
    )
    
    # Use Zen for deep code analysis
    review = await zen_integration.code_review(
        file_path,
        context=past_reviews
    )
    
    # Store the review for future reference
    await memory_service.remember(
        agent_id,
        f"reviews:{file_path}",
        review
    )
    
    return review
```

#### 2. Multi-Agent Consensus with Shared Memory
```python
async def collaborative_planning(task_description):
    # Each agent contributes based on their expertise
    agents = ["product_01", "coder_01", "devops_01"]
    
    contributions = []
    for agent_id in agents:
        # Retrieve agent's relevant memories
        context = await memory_service.search_memories(
            task_description,
            agent_id
        )
        
        # Get agent's perspective
        response = await agent_chat(agent_id, task_description, context)
        contributions.append(response)
    
    # Use Zen's consensus tool to synthesize
    consensus = await zen_integration.consensus(contributions)
    
    # Store the consensus for all agents
    for agent_id in agents:
        await memory_service.remember(
            agent_id,
            f"consensus:{task_description[:50]}",
            consensus
        )
    
    return consensus
```

## 4. Implementation Timeline

### Phase 1: Basic Integration (Week 1)
- [ ] Set up Zen MCP Server with Docker
- [ ] Configure Supermemory API access
- [ ] Update MCP manager to handle new servers
- [ ] Basic tool mapping for agents

### Phase 2: Memory Layer (Week 2)
- [ ] Implement AgentMemoryService
- [ ] Add memory persistence to agent conversations
- [ ] Create memory search functionality
- [ ] Test cross-agent memory sharing

### Phase 3: Advanced Features (Week 3)
- [ ] Integrate Zen's advanced tools (consensus, thinkdeep)
- [ ] Implement smart code review with memory
- [ ] Add collaborative planning features
- [ ] Create memory visualization UI

### Phase 4: Optimization (Week 4)
- [ ] Performance tuning for memory queries
- [ ] Implement memory cleanup/archiving
- [ ] Add memory analytics dashboard
- [ ] Create documentation and examples

## 5. Configuration Requirements

### Environment Variables
```bash
# .env file
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
SUPERMEMORY_API_KEY=your_supermemory_key
```

### Docker Setup
```bash
# Pull Zen MCP Server
docker pull beehiveinnovations/zen-mcp-server

# Run with environment variables
docker run -d \
  --name zen-mcp \
  -p 3000:3000 \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  beehiveinnovations/zen-mcp-server
```

## 6. Expected Outcomes

### Enhanced Agent Capabilities
1. **Coder Agent**: Professional code reviews, intelligent refactoring
2. **Bug Agent**: Advanced debugging with call-flow tracing
3. **Product Agent**: Multi-perspective planning with consensus
4. **All Agents**: Persistent memory and shared knowledge base

### System Benefits
- **Better Context**: Agents remember past interactions
- **Smarter Responses**: Multi-model reasoning for complex tasks
- **Collaborative Intelligence**: Agents can build on each other's knowledge
- **Continuous Learning**: System improves over time through memory

## 7. Monitoring & Maintenance

### Memory Management
- Monitor memory usage and query performance
- Implement periodic memory consolidation
- Set up memory retention policies

### Tool Usage Analytics
- Track which Zen tools are most valuable
- Monitor multi-model usage patterns
- Optimize tool selection based on success rates

### Performance Metrics
- Response time with/without memory enhancement
- Memory hit rate for relevant recalls
- Consensus quality scores
- User satisfaction metrics