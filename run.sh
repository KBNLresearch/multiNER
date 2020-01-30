#!/usr/bin/env bash
cd /
run_external_ners.sh
cd /bin/
gunicorn -w 1 ner:application -b :8099 -t 100
