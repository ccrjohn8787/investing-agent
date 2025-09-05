venv:
	python -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

test:
	pytest -q

demo:
	python scripts/run_synthetic.py

build_i:
	CT=$(CT) python scripts/build_inputs.py

report:
	CT=$(CT) python scripts/report.py
