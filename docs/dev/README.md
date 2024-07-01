# Setup

Install dependencies:

```bash
# first time only
python3 -m venv .venv

poetry install --no-root
```

## Running backend

```bash
poetry run uvicorn app.main:app --port 8000 --reload
```

## Running tests

```bash
poetry run pytest app
```

## Debugging via VSCode

In _Command Pallete_ choose _Debug: Add Configuration_ -> _Python Debugger_ -> _FastAPI_
Set _Application Path_ to: _app.main_
