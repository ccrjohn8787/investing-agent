venv:
	python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

test:
	pytest -q

