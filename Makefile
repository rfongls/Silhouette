# Common development and CI convenience targets
.PHONY: dev test eval lint fmt quant-int8 latency selfcheck selfcheck-student runtime-fastapi runtime-ml runtime-web runtime-python runtime-cpp lint-cpp scoreboard promote-skill traces security-scan

dev:
	python -m cli.main

test:
	pytest -q

eval:
	python -m eval.eval --suite eval/suites/basics.yaml

lint:
        ruff check silhouette_core cli eval training scripts
        black --check silhouette_core cli eval training scripts
        npx eslint .


fmt:
	ruff check . --fix

quant-int8:
	python scripts/quantize.py --method int8 --src ${STUDENT_MODEL:-models/student-core-kd} --out models/student-core-int8

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
        python scripts/scoreboard.py

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
        python -m security.scanner

