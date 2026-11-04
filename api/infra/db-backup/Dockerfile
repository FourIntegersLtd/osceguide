# The nightly off-Railway backup of platform-api's database (docs/SUPPORT-RUNBOOK.md, "Database backups").
#
# Railway's Backups tab does not cover our custom Postgres image, so this cron service dumps the
# database to S3 every night. It is the only copy that survives losing the Railway project.
#
# pg_dump must match the server's major version (17, see ../postgres/Dockerfile): a newer or older
# client refuses or dumps wrongly. Alpine's `postgresql17-client` is 17.x; the base is pinned to the
# release that ships it, so a Debian bump of the client never arrives by surprise.
FROM alpine:3.22

RUN apk add --no-cache postgresql17-client aws-cli

COPY backup.sh /usr/local/bin/backup.sh
RUN chmod +x /usr/local/bin/backup.sh

# Not root: the dump only needs /tmp.
USER nobody
CMD ["/usr/local/bin/backup.sh"]
