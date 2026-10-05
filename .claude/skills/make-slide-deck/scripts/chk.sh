#!/bin/bash
# chk.sh <k>... : re-check each script (rewrite:false); voice every deck whose check has 0 changes (audio tags stay).
# Never bypass the api's 409 "script not checked" refusal.
H=$(cd "$(dirname "$0")" && pwd); W=$(cd "$H/../../../../slide-scripts/work" && pwd); cd "$H"
for k in "$@"; do python3 pipe.py post $(cat $W/d$k.id) write-script '{"rewrite":false}' >/dev/null; done
ok=()
for k in "$@"; do
  python3 pipe.py wait $(cat $W/d$k.id) writing_script $W/z$k.json >/dev/null
  L=$(python3 -c "import json,sys;c=json.load(open('$W/z$k.json'))['content'];s=c.get('review',{}).get('script',{});print(c.get('status'),{k:(v if not isinstance(v,list) else len(v)) for k,v in s.items() if k!='sources'});[print(' -',json.dumps(i)[:300]) for i in s.get('issues',[])]")
  echo "$k $L"
  case "$(echo "$L" | head -1)" in *"'changes': 0"*) ok+=("$k");; esac
done
echo "OK: ${ok[*]}"
for k in "${ok[@]}"; do rm -f $W/v$k.json; python3 pipe.py post $(cat $W/d$k.id) regenerate-av; done
for k in "${ok[@]}"; do python3 pipe.py wait $(cat $W/d$k.id) generating_audio,generating_video $W/v$k.json; done
