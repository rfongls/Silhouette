.PHONY: dev test eval lint fmt

dev:
	python -m cli.main

test:
	pytest -q

eval:
	python -m eval.eval --suite eval/suites/basics.yaml

lint:
	ruff check .

fmt:
	ruff check . --fix
