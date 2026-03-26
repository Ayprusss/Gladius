# Multi-Agent Claude CLI Pipeline (Single Ticket)

## Overview
This project implements a **multi-agent workflow** that processes **one ticket/request end-to-end** using multiple Claude CLI “agents” with specialized roles. Each agent runs as a separate Claude CLI invocation with a distinct prompt and responsibility. The output of one agent becomes structured input for the next agent, forming a simple but powerful pipeline:

**Planner → Implementer → Reviewer**

The workflow is designed to simulate a real engineering loop: understanding a ticket, planning a solution, implementing changes, and reviewing them for quality and risk.

---

## Atlassian MCP Integration
The Google Claude CLI used in this project is connected to an **Atlassian MCP (Model Context Protocol) server**, enabling agents to **directly query and reason over Atlassian data** such as:

- Jira tickets and descriptions
- Acceptance criteria and custom fields
- Ticket comments and status history
- Linked issues, epics, and related context

This allows the pipeline to operate on **live or realistic ticket data** rather than static text inputs.

**Key benefits:**
- Planner agents can fetch full ticket context automatically
- Implementer agents can reference acceptance criteria directly
- Reviewer agents can verify whether changes satisfy the original Jira request
- Reduces manual copying of ticket data into prompts

The MCP server acts as a structured, read-only context provider for the agents, improving accuracy and realism of the workflow.

---

## Idea B Summary (Single Ticket Pipeline)
### What it does
Given a single ticket (bug report, feature request, or refactor request), the workflow:
1. **Plans** the solution (clarifies requirements, proposes approach, identifies risks)
2. **Implements** a proposed change (generates patch/code + explanation)
3. **Reviews** the implementation (correctness, style, security, edge cases, tests)

Each stage is handled by a different agent prompt with strict role boundaries and structured outputs.

---

## Key Concepts
### 1) Agents as CLI invocations
Each “agent” is a **separate Claude CLI call** with:
- A role-specific prompt
- A constrained output format (JSON)
- Access to ticket context via the Atlassian MCP server

Agents do not share memory directly; all coordination happens through structured outputs.

---

### 2) Chained, structured outputs
Each agent returns **machine-readable JSON**, enabling:
- Validation and retries on malformed output
- Deterministic handoff between stages
- Persisted artifacts for demos and auditing

---

### 3) Orchestrator as the coordinator
A lightweight orchestrator script:
- Loads or fetches the ticket (via MCP)
- Calls Claude CLI for each agent
- Validates and persists outputs
- Produces a final summarized report

---

## Pipeline Stages
### Stage 1: Planner Agent
**Purpose:** Convert the raw ticket into a clear, actionable plan.

**Input:**
- Jira ticket context (via Atlassian MCP)
- Optional: code snippets, logs, constraints

**Output:**
- `summary`
- `assumptions`
- `plan`
- `files_to_change`
- `test_plan`
- `risks`

---

### Stage 2: Implementer Agent
**Purpose:** Generate a proposed implementation based on the plan.

**Input:**
- Ticket context
- Planner output
- Optional: repository code context

**Output:**
- `changes`
- `patch` (unified diff preferred)
- `notes`
- `tests_added_or_updated`

---

### Stage 3: Reviewer Agent
**Purpose:** Perform a strict review of the proposed solution.

**Input:**
- Ticket context
- Planner output
- Implementer output

**Output:**
- `review_summary`
- `issues`
- `suggested_changes`
- `verdict` (`APPROVE` or `REQUEST_CHANGES`)

---

## Suggested Tech Stack
### Recommended
- **Python**
  - Orchestration logic
  - Claude CLI invocation
  - JSON parsing and validation
  - Artifact persistence

### Alternative
- **Node.js / TypeScript**
  - Strong typing for pipeline stages
  - Async process management

---

## Outputs and Artifacts
Each run produces:
- `runs/<run_id>/ticket.json`
- `runs/<run_id>/planner.json`
- `runs/<run_id>/implementer.json`
- `runs/<run_id>/reviewer.json`
- `runs/<run_id>/final_report.md`

These artifacts make the workflow transparent, auditable, and demo-friendly.

---

## Why this is feasible
This project is feasible because:
- Claude CLI can be invoked programmatically
- Atlassian MCP provides structured access to ticket data
- Agents are isolated through prompts and JSON contracts
- Orchestration is standard scripting

The main challenges are enforcing JSON outputs, handling retries, and managing context size.

---

## MVP Implementation Plan
1. Define agent prompt templates
2. Implement orchestrator script
3. Fetch ticket data via Atlassian MCP
4. Execute Planner → Implementer → Reviewer
5. Persist results and generate summary

---

## Possible Extensions
- Multiple planners or reviewers with result merging
- Automatic PR generation
- Jira comment updates with results
- CI test execution after implementation
- Metrics on approval vs rework rates

---

## Summary
This project demonstrates a **single-ticket, multi-agent development workflow** powered by the Google Claude CLI and Atlassian MCP:

- Planner: understands and plans the ticket
- Implementer: proposes a concrete solution
- Reviewer: evaluates correctness and quality

The result is a realistic, extensible AI-assisted engineering pipeline suitable for hackathons and internal tooling.
