# {{project_name}}

{{project_description}}

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Virtual environment (`venv` or `uv`)

### 2. Setup
```bash
# Copy environment variables
cp .env.example .env

# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### 3. Usage
```bash
python -m {{package_name}}.main
```

## Project Structure
```text
├── docs/
│   └── architecture.md
├── src/
│   └── {{package_name}}/
│       ├── __init__.py
│       ├── agent.py
│       ├── config.py
│       └── main.py
├── tests/
│   ├── __init__.py
│   └── test_agent.py
├── .env.example
├── .gitignore
└── pyproject.toml
```
