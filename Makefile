# Common development and CI convenience targets
.PHONY: dev test eval lint fmt quant-int8 latency selfcheck selfcheck-student

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

quant-int8:
	python scripts/quantize.py --method int8 --src $${STUDENT_MODEL:-models/student-core-kd} --out models/student-core-int8

latency:
        python scripts/latency_probe.py

selfcheck:
	python scripts/selfcheck.py --policy profiles/core/policy.yaml

selfcheck-student:
        STUDENT_MODEL=models/student-core-kd python scripts/selfcheck.py --policy profiles/core/policy.yaml
