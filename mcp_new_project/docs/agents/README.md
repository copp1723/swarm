# Agent Reference Guide

This guide provides detailed information about each specialized agent in the MCP Multi-Agent System.

## Overview

The system includes 6 specialized AI agents, each designed for specific aspects of software development:

| Agent | Specialty | Best For |
|-------|-----------|----------|
| [Architect](#architect) | System Design | Planning, architecture, high-level design |
| [Developer](#developer) | Implementation | Coding, debugging, feature development |
| [QA Engineer](#qa-engineer) | Testing | Test planning, bug finding, quality assurance |
| [Security Analyst](#security-analyst) | Security | Vulnerability assessment, threat modeling |
| [DevOps Engineer](#devops-engineer) | Infrastructure | Deployment, CI/CD, automation |
| [General Assistant](#general-assistant) | Versatile | Any task, quick questions, general help |

## Architect (planner_01) {#architect}

### Role & Expertise
The Architect specializes in high-level system design and strategic planning. This agent excels at breaking down complex requirements into modular, scalable architectures.

### Key Capabilities
- **System Design**: Creates comprehensive architectural patterns (microservices, monolithic, event-driven)
- **Planning**: Develops detailed project roadmaps and technical specifications
- **Analysis**: Evaluates existing systems and proposes improvements
- **Documentation**: Produces clear architectural diagrams and design documents

### Best Practices
- Use for initial project planning and design decisions
- Ask for specific architectural patterns for your use case
- Request design trade-off analysis
- Get recommendations for technology stack selection

### Example Prompts
```
"Design a scalable microservices architecture for an e-commerce platform"

"Analyze this codebase and suggest architectural improvements"

"Create a migration plan from monolith to microservices"
```

### Preferred Models
- **Claude 4 Opus**: Best for complex architectural decisions
- **GPT 4.1**: Excellent for detailed technical specifications
- **O3 Pro**: Advanced reasoning for design trade-offs

## Developer (coder_01) {#developer}

### Role & Expertise
The Developer is your implementation specialist, focusing on writing clean, efficient code and solving technical problems.

### Key Capabilities
- **Coding**: Implements features in multiple programming languages
- **Debugging**: Identifies and fixes bugs with detailed explanations
- **Refactoring**: Improves code quality and performance
- **Integration**: Connects systems and APIs effectively

### Best Practices
- Provide clear requirements and context
- Share relevant code snippets or file paths
- Ask for explanations of implementation choices
- Request unit tests along with code

### Example Prompts
```
"Implement a REST API endpoint for user authentication"

"Debug this Python function that's causing a memory leak"

"Refactor this code to follow SOLID principles"
```

### Preferred Models
- **DeepSeek R1**: Optimized for coding tasks
- **DeepSeek V3**: Advanced code generation
- **Codex Mini**: Fast, efficient coding assistance

## QA Engineer (tester_01) {#qa-engineer}

### Role & Expertise
The QA Engineer ensures software quality through comprehensive testing strategies and bug identification.

### Key Capabilities
- **Test Planning**: Creates detailed test plans and strategies
- **Bug Detection**: Identifies edge cases and potential issues
- **Test Automation**: Designs automated test suites
- **Performance Testing**: Evaluates system performance and scalability

### Best Practices
- Provide clear acceptance criteria
- Share the code or feature to be tested
- Ask for both positive and negative test cases
- Request specific testing frameworks recommendations

### Example Prompts
```
"Create a comprehensive test plan for this login feature"

"Write unit tests for this payment processing module"

"Identify potential edge cases in this data validation function"
```

### Preferred Models
- **GPT 4.1**: Thorough test case generation
- **O3 Pro**: Advanced test scenario analysis
- **Claude 4 Sonnet**: Efficient QA processes

## Security Analyst (security_01) {#security-analyst}

### Role & Expertise
The Security Analyst specializes in identifying vulnerabilities and implementing security best practices.

### Key Capabilities
- **Vulnerability Assessment**: Identifies security flaws in code and systems
- **Threat Modeling**: Analyzes potential attack vectors
- **Security Reviews**: Conducts comprehensive security audits
- **Compliance**: Ensures adherence to security standards (OWASP, NIST)

### Best Practices
- Share specific code or configurations for review
- Ask for severity ratings on identified issues
- Request mitigation strategies
- Get compliance checklist reviews

### Example Prompts
```
"Review this authentication system for security vulnerabilities"

"Perform a security audit on this REST API"

"Create a threat model for this application"
```

### Preferred Models
- **GPT 4.1**: Comprehensive security analysis
- **Claude 4 Opus**: Deep security insights
- **O3 Pro**: Advanced threat analysis

## DevOps Engineer (devops_01) {#devops-engineer}

### Role & Expertise
The DevOps Engineer handles infrastructure, deployment, and operational excellence.

### Key Capabilities
- **CI/CD**: Designs and implements deployment pipelines
- **Infrastructure as Code**: Creates Terraform, CloudFormation scripts
- **Containerization**: Docker and Kubernetes configurations
- **Monitoring**: Sets up logging and monitoring solutions

### Best Practices
- Specify your cloud platform (AWS, GCP, Azure)
- Share existing infrastructure details
- Ask for automation scripts
- Request cost optimization strategies

### Example Prompts
```
"Create a CI/CD pipeline for this Node.js application"

"Write Kubernetes deployment configs for a microservices app"

"Set up monitoring and alerting for production environment"
```

### Preferred Models
- **GPT 4.1**: Infrastructure planning
- **O3 Pro**: Advanced automation
- **Codex Mini**: Script generation

## General Assistant (general_01) {#general-assistant}

### Role & Expertise
The General Assistant is a versatile agent that can handle any task, making it perfect for quick questions or tasks that don't fit neatly into other specialties.

### Key Capabilities
- **Versatility**: Handles any type of query or task
- **Research**: Gathers information and provides summaries
- **Documentation**: Creates and updates documentation
- **Problem Solving**: Tackles unique or cross-functional challenges

### Best Practices
- Use for tasks that span multiple domains
- Great for initial exploration of problems
- Helpful for documentation and explanations
- Good fallback when unsure which specialist to use

### Example Prompts
```
"Explain how this project works to a new developer"

"Create README documentation for this repository"

"Help me understand this error message"
```

### Preferred Models
- **GPT 4.1**: All-around performance
- **Claude 4 Opus**: Excellent reasoning
- **Gemini 2.5 Pro**: Latest capabilities

## Collaborative Workflows

Agents work best together. Here are effective agent combinations:

### Full Stack Development
1. **Architect** → Design system architecture
2. **Developer** → Implement features
3. **QA Engineer** → Test implementation
4. **DevOps** → Deploy to production

### Security Review
1. **Security Analyst** → Identify vulnerabilities
2. **Developer** → Fix security issues
3. **QA Engineer** → Verify fixes
4. **Architect** → Update security architecture

### Code Modernization
1. **Architect** → Plan migration strategy
2. **Developer** → Refactor code
3. **QA Engineer** → Ensure functionality preserved
4. **DevOps** → Update deployment processes

## Tips for Effective Agent Use

### 1. Be Specific
- Provide clear context and requirements
- Share relevant file paths and code snippets
- State your expected outcome

### 2. Use the Right Agent
- Match agent specialty to your task
- Consider using multiple agents for complex tasks
- Start with General Assistant if unsure

### 3. Iterate and Refine
- Build on agent responses
- Ask follow-up questions
- Request clarifications when needed

### 4. Leverage Collaboration
- Use sequential workflows for dependent tasks
- Enable agents to build on each other's work
- Review collective output for best results

## Model Selection Guide

### Speed vs Quality Trade-offs

**Fast Response** (< 5 seconds):
- Codex Mini
- Claude 4 Sonnet
- DeepSeek V3

**Balanced** (5-15 seconds):
- GPT 4.1
- DeepSeek R1
- Gemini 2.5 Pro

**Highest Quality** (15-30 seconds):
- Claude 4 Opus
- O3 Pro
- Grok 3

### Specialized Tasks

**Best for Coding**:
1. DeepSeek R1
2. Codex Mini
3. GPT 4.1

**Best for Analysis**:
1. Claude 4 Opus
2. O3 Pro
3. GPT 4.1

**Best for Speed**:
1. Codex Mini
2. Claude 4 Sonnet
3. DeepSeek V3

## Advanced Features

### File Upload
Each agent can analyze uploaded files:
- Source code files for review
- Configuration files for analysis
- Documentation for understanding
- Logs for debugging

### Filesystem Access
Agents have access to `/Users/copp1723/Desktop`:
- Can read and analyze project files
- Understand directory structures
- Reference specific file contents
- Suggest file modifications

### Workflow Templates
Pre-configured multi-agent workflows:
- Code Review Workflow
- Security Audit Workflow
- Full Stack Development
- Bug Fix Workflow
- Documentation Update

Access these through the Collaboration Hub interface.