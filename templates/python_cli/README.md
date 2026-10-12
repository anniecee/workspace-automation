# {{project_name}}

{{project_description}}

## Installation & Setup

```bash
# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install CLI in editable mode
pip install -e ".[dev]"
```

## Usage

```bash
# Run via console script
{{project_name}} --help

# Or run directly with python
python -m {{package_name}} --help
```
