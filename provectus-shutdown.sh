#!/bin/bash
PATH=/usr/bin:/bin:/usr/local/bin

/usr/bin/curl -s \
  -H "Priority: high" \
  -H "Title: Provectus" \
  -d "Status: NOTEBOOK DESLIGANDO 🔴" \
  ntfy.sh/provectus
