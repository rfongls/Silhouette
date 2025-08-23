#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 artifacts/<ts>/silhouette_run.json" >&2
  exit 1
fi
json="$1"
cmd=$(python - "$json" <<'PY'
import json,sys
with open(sys.argv[1]) as f:
    data=json.load(f)
print(data["command"])
PY
)
if [ "$cmd" = "repo_map" ]; then
  args=$(python - "$json" <<'PY'
import json,sys
with open(sys.argv[1]) as f:
    data=json.load(f)
parts=[]
for k,v in data["args"].items():
    flag='--'+k.replace('_','-')
    if isinstance(v,bool):
        if v:
            parts.append(flag)
    else:
        parts.extend([flag,str(v)])
print(' '.join(parts))
PY
)
  repo_root=$(python - "$json" <<'PY'
import json,sys
with open(sys.argv[1]) as f:
    data=json.load(f)
print(data["repo_root"])
PY
)
  python -m silhouette_core.cli repo map "$repo_root" $args
else
  echo "Unsupported command: $cmd" >&2
  exit 1
fi
