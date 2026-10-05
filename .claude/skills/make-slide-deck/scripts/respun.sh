#!/bin/bash
# respun.sh <k>... : check respun decks, put back their narration after the check's rewrite, then check and voice.
# The first check rewrites every changed slide; `respin.py <k> keep` restores the lines from want<k>.json and
# the second, full check voices each deck it passes (chk.sh), reusing the saved audio for unchanged lines.
H=$(cd "$(dirname "$0")" && pwd); cd "$H"
bash chk.sh "$@"
for k in "$@"; do python3 respin.py $k keep; done
bash chk.sh "$@"
