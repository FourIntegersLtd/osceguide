#!/bin/sh
# Nightly logical backup of platform-api's database to S3. Exits non-zero on any failure.
#
# Needs (service variables; the database and AWS ones are Railway references, never copied values):
#   DATABASE_URL            the database's private-network URL
#   BACKUP_ENV              staging | production: the folder the dump lands in
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Optional: AWS_REGION (default eu-west-2), BACKUP_RETENTION_DAYS (default 30).
#
# Prints sizes and keys only. Never prints DATABASE_URL or a credential.
set -eu

: "${DATABASE_URL:?DATABASE_URL is not set}"
: "${BACKUP_ENV:?BACKUP_ENV is not set}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is not set}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is not set}"

case "$BACKUP_ENV" in
  staging | production) ;;
  *) echo "BACKUP_ENV must be staging or production" >&2; exit 2 ;;
esac

# Same bucket and region as app/core/bucket_layout.py (a shell script cannot import it). The prefix
# below is the only place this script writes or deletes.
BUCKET="osceguide-platform"
PREFIX="db-backups/nightly/${BACKUP_ENV}/"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
export AWS_DEFAULT_REGION="${AWS_REGION:-eu-west-2}"

TODAY="$(date -u +%Y-%m-%d)"
KEY="${PREFIX}${TODAY}.dump"
FILE="$(mktemp /tmp/backup.XXXXXX)"
trap 'rm -f "$FILE"' EXIT

echo "dumping ${BACKUP_ENV}"
# A file, not a pipe into aws: plain sh has no pipefail, and a pipe would upload a truncated dump
# as a success when pg_dump dies half way.
pg_dump --dbname="$DATABASE_URL" -Fc --no-owner --no-privileges --file="$FILE"
LOCAL_BYTES="$(wc -c < "$FILE" | tr -d ' ')"
[ "$LOCAL_BYTES" -gt 0 ] || { echo "dump is empty" >&2; exit 1; }
# The dump's table of contents must read back: catches a file that is not a complete archive.
pg_restore -l "$FILE" > /dev/null
echo "dump bytes=${LOCAL_BYTES}"

aws s3 cp "$FILE" "s3://${BUCKET}/${KEY}" --sse AES256 --only-show-errors
REMOTE_BYTES="$(aws s3api head-object --bucket "$BUCKET" --key "$KEY" --query ContentLength --output text)"
if [ "$REMOTE_BYTES" != "$LOCAL_BYTES" ]; then
  echo "upload size mismatch: local=${LOCAL_BYTES} remote=${REMOTE_BYTES}" >&2
  exit 1
fi
echo "uploaded key=${KEY} bytes=${REMOTE_BYTES}"

# Retention: only after today's dump is verified, only dated nightly keys of this environment, and by
# the date in the key name (not LastModified, which a copy would reset).
CUTOFF="$(date -u -d "@$(( $(date +%s) - RETENTION_DAYS * 86400 ))" +%Y-%m-%d)"
# Listed into a file first: plain sh has no pipefail, so a failed listing in a pipe would end the
# run as a success with nothing pruned.
LISTING="$(mktemp /tmp/listing.XXXXXX)"
trap 'rm -f "$FILE" "$LISTING"' EXIT
aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "$PREFIX" --query 'Contents[].Key' --output text > "$LISTING"
tr '\t' '\n' < "$LISTING" \
  | { grep -E "^${PREFIX}[0-9]{4}-[0-9]{2}-[0-9]{2}\.dump$" || true; } \
  | while read -r old; do
      day="${old#"$PREFIX"}"
      day="${day%.dump}"
      if [ "$day" \< "$CUTOFF" ]; then
        aws s3api delete-object --bucket "$BUCKET" --key "$old" > /dev/null
        echo "deleted key=${old}"
      fi
    done

echo "done"
