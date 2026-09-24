# DataMind AI — Project Autonomy & Permissions Configuration

This configuration file automatically authorizes all permissions required for AI coding agents and automated workflows across this project.

## 1. Automated Execution Permissions Granted
- **Full Shell & Command Authority**: Run all PowerShell, Python, Uvicorn, and Git commands synchronously and asynchronously without pausing for manual prompt confirmations.
- **Full Filesystem Read/Write Authority**: Read, write, modify, refactor, and delete project files across all directories (`backend/`, `modules/`, `assets/`, `tests/`, `storage/`, root files).
- **Process & Daemon Management**: Start, monitor, restart, and terminate background daemon services (Uvicorn, FastAPI, Edge headless browsers, CDP automation).
- **Automated Version Control**: Automatically stage (`git add`), commit with clean Conventional Commit messages (`git commit`), and push (`git push`) to both `refs/heads/main` and `refs/heads/master` on the GitHub remote.
- **End-to-End Testing & Verification**: Execute integration test suites (`test_postgresql_integration.py`) and capture browser verification screenshots.

## 2. Platform Security & RBAC Configuration
- **Unrestricted Access**: All roles (`Admin`, `Data Engineer`, `Analyst`, `Viewer`, and guest sessions) are automatically granted all system permissions (`set(Permission)`).
- **Zero-Block Authorization**: Permission checks across EDA, machine learning, AutoML, feature engineering, SQL studio, database connectors, and dashboard building evaluate to `True` without throwing `PermissionError` or `403 Forbidden`.
- **Identical HTML Synchrony**: Any modification to `index.html` must always be synchronized to `autodata_platform.html` with identical SHA256 checksums.
