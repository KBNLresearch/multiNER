sudo "echo 1 > /proc/sys/ipv4/tcp_tw_recycle"
while true; do gunicorn -w 10 ner:application -b :8099;done


