# OLP XDV Pipeline Swarm Orchestration Plan

## Current State Analysis
The OLP XDV pipeline currently uses a strictly sequential approach where each agent calls the next in a linear fashion (Agent 1 → Agent 2 → ... → Agent 10). This creates several issues:

1. **No Fault Tolerance**: If any agent fails, the entire pipeline stops
2. **No Parallel Execution**: Agents that could run independently must wait for predecessors
3. **Tight Coupling**: Agents are coupled through direct function calls
4. **Limited Visibility**: Hard to monitor individual agent performance
5. **No State Persistence**: Intermediate states aren't persisted for recovery

## Proposed Solution: Ruflo Swarm Orchestration
Apply ruflo's swarm patterns to decouple agents and enable more resilient execution:

### 1. Swarm Topology
Use **hierarchical-mesh** topology (recommended for 10+ agents):
- Queen agent maintains authoritative state
- Peer communication between agents for resilience
- Clear role boundaries with specialized agents

### 2. Agent Specialization
Map the 10 pipeline agents to ruflo specialized agents:
- Agent 1 (Macro Ingestion) → researcher + coder
- Agent 2 (Whitelist Filter) → coder  
- Agent 3 (Entity Profiling) → coder + tester
- Agent 4 (Data Verification) → tester + reviewer
- Agent 5 (XDV Logic Core) → architect + coder
- Agent 6 (Odds & Line Audit) → security-auditor + tester
- Agent 7 (Compliance Sentinel) → security-architect + reviewer
- Agent 8 (Execution Controller) → coder + tester
- Agent 9 (Team Lead Orchestrator) → planner + reviewer
- Agent 10 (Executive CEO) → architect (final approval)

### 3. Implementation Approach
Modify the pipeline to use ruflo's swarm coordination:

#### Step 1: Initialize Swarm
```bash
npx @claude-flow/cli@latest swarm init --topology hierarchical-mesh --max-agents 12 --strategy specialized
```

#### Step 2: Define Agent Tasks
Create specialized tasks for each pipeline stage with clear handoffs:

#### Step 3: Implement Memory-Based State Passing
Use AgentDB/HNSW for state persistence between agents instead of direct function calls

#### Step 4: Add Error Handling and Retry Logic
Leverage ruflo's built-in failure detection and recovery mechanisms

#### Step 5: Enable Parallel Execution Where Safe
Identify stages that can run concurrently (e.g., multiple league processing)

## Benefits
1. **Fault Tolerance**: Pipeline continues even if individual agents fail
2. **Performance**: Parallel execution where dependencies allow
3. **Observability**: Clear visibility into each agent's status and performance
4. **Recovery**: Persistent state enables pipeline resumption after interruptions
5. **Scalability**: Easy to add new agents or modify existing ones

## Files to Modify
1. `olp_xdv_pipeline.py` - Main orchestration logic
2. Create new agent definition files in `.claude/agents/` for specialized roles
3. Update `CLAUDE.md` to document the new swarm-based approach
4. Create coordination scripts in `scripts/` directory

## Risk Mitigation
- Maintain backward compatibility during transition
- Test with `--dry-run` flag before enabling production mode
- Monitor knowledge persistence to ensure state isn't lost
- Gradually roll out changes agent by agent