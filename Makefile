# Common development and CI convenience targets
.PHONY: dev engine-dev install build wheel sdist clean repl test eval lint fmt quant-int8 quant-onnx quant-gguf latency latency-edge selfcheck selfcheck-student runtime-fastapi runtime-ml runtime-web runtime-python runtime-cpp runtime-java-ext runtime-dotnet-ext runtime-android-ext lint-cpp scoreboard scoreboard-phase scoreboard-phase6 promote-skill traces traces-promote security-scan gates research-index research-eval

dev:
	python -m pip install -U pip
	pip install -e .[all]

engine-dev:
	./scripts/dev_engine.sh

install:
	pip install .

build:
	python -m build

wheel:
	python -m build --wheel

sdist:
	python -m build --sdist

clean:
	rm -rf build/ dist/ *.egg-info

repl:
	python -m cli.main

test:
	pytest -q

eval:
	python -m eval.eval --suite eval/suites/basics.yaml

lint:
	ruff check silhouette_core cli eval training scripts engine insights
	black --check silhouette_core cli eval training scripts engine insights
	npx eslint .

fmt:
	ruff check . --fix

quant-int8:
	python scripts/quantize.py --method int8 --src models/student-core-kd --out models/student-core-int8

quant-onnx:
	python scripts/quantize.py --method onnx-int8 --src models/student-core-kd --out models/student-core-onnx

quant-gguf:
	python scripts/quantize.py --method gguf --src models/student-core-kd --out models/student-core-gguf

latency:
	python scripts/latency_probe.py

latency-edge:
	SILHOUETTE_EDGE=1 STUDENT_MODEL=models/student-core-int8 python scripts/latency_probe.py

selfcheck:
	python scripts/selfcheck.py --policy profiles/core/policy.yaml

selfcheck-student:
	STUDENT_MODEL=models/student-core-kd python scripts/selfcheck.py --policy profiles/core/policy.yaml

runtime-fastapi:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_python_fastapi_runtime.yaml

runtime-ml:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_python_ml_runtime.yaml

runtime-web:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_web_runtime.yaml

runtime-python:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_python_runtime.yaml

runtime-cpp:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_cpp_runtime.yaml

lint-cpp:
	clang-tidy **/*.cpp -- -std=c++17

runtime-java-ext:
	ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_java_runtime_ext.yaml

runtime-dotnet-ext:
        ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_dotnet_runtime_ext.yaml

runtime-android-ext:
        ENABLE_RUNTIME_EVAL=1 python -m eval.build_runner --suite eval/suites/dev_android_runtime_ext.yaml

scoreboard:
	python scripts/scoreboard.py && python scripts/scoreboard_history.py

scoreboard-phase:
	PHASE=${PHASE} python scripts/scoreboard.py

scoreboard-phase6:
	PHASE=phase-6 python scripts/scoreboard.py && python scripts/scoreboard_history.py

promote-skill:
	python scripts/promote_skill_version.py --name $(NAME) --from_version $(FROM) --to_version $(TO)

traces:
	python scripts/synthesize_traces.py
	python scripts/validate_traces.py artifacts/traces/runtime_kd.jsonl

security-scan:
	python -m silhouette_core.security.scanner

traces-promote:
        python scripts/promote_traces.py --lane python
        python scripts/promote_traces.py --lane java
        python scripts/promote_traces.py --lane dotnet
        python scripts/promote_traces.py --lane android
        python scripts/promote_traces.py --lane web
        python scripts/promote_traces.py --lane cpp

gates:
        python scripts/regression_gate.py --report artifacts/scoreboard/latest.json --previous artifacts/scoreboard/previous.json

research-index:
	python scripts/research_index_corpus.py docs/corpus

research-eval:
        silhouette eval --suite eval/suites/research_grounded.yaml

license:
        python scripts/issue_customer_license.py --customer-id TEST123

cyber-scope:
	@echo "192.168.1.10" > docs/cyber/scope_example.txt

cyber-nmap:
	SILHOUETTE_PEN_TEST_OK=1 silhouette run --profile profiles/core/policy.yaml

cyber-eval:
        silhouette eval --suite eval/suites/cyber_safe_modes.yaml
        silhouette eval --suite eval/suites/cyber_smoke.yaml || true
cdse-index:
        python scripts/cdse_build_index.py

cyber-task-web-dry:
        SILHOUETTE_PEN_TEST_OK=1 silhouette run
        # In REPL:
        # > use:cyber_task_orchestrator {"task":"web_baseline","target":"https://in-scope.example","scope_file":"docs/cyber/scope_example.txt","dry_run":true}


setup:
	pip install -r requirements.txt
	pip install pytest ruff

docs:
	python scripts/export_mermaid.py docs/

schemas:
	@echo "JSON Schemas located in schemas/fhir/uscore/"

.PHONY: test-hl7 e2e

test-hl7:
	pytest -q -m hl7 --maxfail=1

e2e:
	pytest -q -m "hl7 and slow" --maxfail=1
