# {{project_name}}

{{project_description}}

## Setup

```bash
# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install editable package
pip install -e ".[dev]"
```

## Structure
```text
├── docs/
├── src/
│   └── {{package_name}}/
│       ├── __init__.py
│       └── core.py
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── .gitignore
└── pyproject.toml
```
