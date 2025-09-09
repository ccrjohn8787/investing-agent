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

# Acceptance/Canary tests
acceptance:
	pytest -q tests/acceptance

# Eval JSON report
eval_report:
	python scripts/eval_report.py --out out/eval_summary.json

# Golden canaries
golden:
	python scripts/write_canary.py $(PATH)

golden_check:
	pytest -q -k canaries_golden

demo:
	python scripts/run_synthetic.py

build_i:
	CT=$(CT) python scripts/build_inputs.py

report:
	@source .venv/bin/activate && export PYTHONPATH=$(PWD):$$PYTHONPATH && CT=$(CT) python scripts/report.py

supervisor:
	CT=$(CT) python scripts/supervisor.py --html

router_demo:
	python scripts/router_demo.py

ui:
	python scripts/make_index.py && echo "Open out/index.html"

# Report Quality Evaluation Commands
eval_quality:
	@echo "Generating report and evaluating quality for $(CT)..."
	@$(MAKE) report CT=$(CT)
	@python scripts/eval_quality.py --ticker $(CT)

eval_quality_only:
	@echo "Evaluating quality for existing $(CT) report..."
	@python scripts/eval_quality.py --ticker $(CT) --skip-generation

eval_quality_batch:
	@echo "Batch evaluating reports for: $(CT)"
	@for ticker in $$(echo "$(CT)" | tr "," " "); do \
		echo "Evaluating $$ticker..."; \
		$(MAKE) eval_quality_only CT=$$ticker; \
	done

test_quality_evals:
	@echo "Running all report quality evaluation tests..."
	@pytest -q tests/evals/test_report_quality_evals.py -v

# Quick report generation for eval testing
quick_report:
	@echo "Generating quick report for $(CT) (cached data, minimal processing)..."
	@CT=$(CT) python scripts/report.py --quick --cache-only
