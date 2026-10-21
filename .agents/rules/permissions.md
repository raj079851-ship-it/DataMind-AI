---
trigger: always_on
---

# Antigravity Autonomous Execution & Permission Policy

This rule governs agent execution autonomy, permission management, and safety protocols for this project.

## 1. Task-Level Approval & Scope Autonomy
- **Single Task Approval**: Once a user requests, assigns, or approves a task or workflow, the agent has full authorization to execute all subsequent steps that fall within that approved scope without pausing for repeated permissions.
- **Continuous Multi-Step Execution**: Complete multi-step chains (reading, editing, debugging, building, testing, verifying, and committing) autonomously from start to finish.

## 2. Unrestricted Routine Actions
Proceed without manual prompt confirmations for safe, routine development tasks:
- **Read & Analyze**: Inspecting files, logs, repository history, schemas, dependencies, and project artifacts.
- **Create & Edit**: Writing, refactoring, editing, and organizing source code across frontend and backend modules.
- **Code Hygiene & Verification**: Running linters, formatters, static analyzers, and non-destructive automated test suites (e.g. pytest, CDP scripts).
- **Environment & Build**: Running approved build, dev, and environment commands (PowerShell, Python, Uvicorn, Vite/Webpack, Git).
- **Autonomous Error Resolution**: When an error or test failure occurs, inspect logs, diagnose root cause, and apply safe corrections independently without interrupting the user at each debugging step.

## 3. High-Risk / Sensitive Boundaries (Explicit Approval Required)
The agent must stop and solicit explicit user authorization before:
- Destructive operations (e.g., dropping databases, recursive deletion of untracked directories, `git reset --hard` destroying uncommitted user work).
- Deleting core project documentation or production configuration files.
- Exposing secrets, API keys, private tokens, or credentials in plaintext logs or outputs.
- Making external financial purchases, signing up for paid external services, or altering system-level security/firewall configurations.
- Actions falling fundamentally outside the requested task scope.

## 4. Execution Reporting & Progress Updates
- Execute tasks efficiently and autonomously.
- Provide concise, structured progress summaries upon completion: what was executed, what changed, how it was verified, and any open decisions requiring user choice.
