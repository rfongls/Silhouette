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

runtime-fastapi:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_python_fastapi_runtime.yaml

runtime-ml:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_python_ml_runtime.yaml
