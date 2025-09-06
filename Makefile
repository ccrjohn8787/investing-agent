venv:
	python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

.PHONY: test lint fmt ci
test:
	pytest -q

lint:
	ruff check .

fmt:
	ruff format .

ci:
	ruff check . && mypy investing_agent && pytest -q

eval:
	pytest -q -m eval

demo:
	python scripts/run_synthetic.py

build_i:
	CT=$(CT) python scripts/build_inputs.py

report:
	CT=$(CT) python scripts/report.py

supervisor:
	CT=$(CT) python scripts/supervisor.py --html

router_demo:
	python scripts/router_demo.py
