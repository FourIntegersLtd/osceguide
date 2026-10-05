#!/bin/bash
# pub.sh <k> [slide_id] : download the finished mp4, sync the deck JSON, publish to staging, production and legacy Firestore.
# With a slide_id, the rebuilt deck replaces that published deck in all three places (same ids, no copies).
H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../../../.." && pwd)
R=$ROOT/slide-scripts; W=$R/work; A=$ROOT/api
k=$1; deck=$(cat $W/d$k.name); nn=${deck%%-*}
cd $A || exit 1
st=$(python3 -c "import json;c=json.load(open('$W/v$k.json'))['content'];print(c.get('status'),c.get('final_video_url') or '')")
url=${st#* }
case "$st" in completed*) ;; *) echo "SKIP $k: $st"; exit 1;; esac
curl -sf -o $R/$nn-full-deck-ben.mp4 "$url" || { echo "download failed"; exit 1; }
python3 $H/sync.py $W/v$k.json $R/$deck.json | tail -1
SID=$(PYTHONPATH=. poetry run python $H/mkpub.py $W/v$k.json $2 | tail -1)
echo "$k $deck SID=$SID"
if [ -n "$2" ]; then REPL=--replace; echo "$k $deck $SID replaced $(date +%F)" >> $W/published.txt; else REPL=; echo "$k $deck $SID" >> $W/published.txt; fi
railway run -s platform-postgres -e staging poetry run python ../slide-scripts/tools/publish_deck.py platform --slide-id $SID --database-url-env RAILWAY_PROXY --live 2>&1 | tail -2
railway run -s platform-postgres-production -e production poetry run python ../slide-scripts/tools/publish_deck.py platform --slide-id $SID --database-url-env RAILWAY_PROXY --live 2>&1 | tail -2
FIREBASE_SERVICE_ACCOUNT_KEY_PATH=$ROOT/service-key PYTHONPATH=. poetry run python ../slide-scripts/tools/publish_deck.py firestore --slide-id $SID --apply $REPL 2>&1 | tail -2
