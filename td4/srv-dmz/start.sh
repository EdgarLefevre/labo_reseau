#!/bin/sh
printf 'HTTP/1.1 200 OK\r\nContent-Length: 7\r\n\r\nDMZ OK\n' > /tmp/reponse.txt
nohup socat TCP-LISTEN:443,fork,reuseaddr SYSTEM:"cat /tmp/reponse.txt" > /dev/null 2>&1 &
