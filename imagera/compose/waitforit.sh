#!/usr/bin/env bash


MAX_TRIES=5  # Maximum number of attempts
WAIT_INTERVAL=25  # Interval between attempts in seconds
QUIET=0
TIMEOUT=30
POST_SUCCESS_WAIT=1  # Additional wait time after successful connection (in seconds)

usage() {
  echo "Usage: wait-for-it.sh host:port [-t timeout] [-q]"
  exit 1
}

while getopts "t:q" opt; do
  case "$opt" in
    t) TIMEOUT="$OPTARG" ;;
    q) QUIET=1 ;;
    *) usage ;;
  esac
done

shift $((OPTIND - 1))

HOST=$1
if [ -z "$HOST" ]; then
  usage
fi

HOST_ARR=(${HOST//:/ })
HOST=${HOST_ARR[0]}
PORT=${HOST_ARR[1]}

if [ "$QUIET" -eq 0 ]; then
  echo "Waiting for $HOST:$PORT..."
fi

for try in $(seq 1 $MAX_TRIES); do
  for i in $(seq 1 $TIMEOUT); do
    nc -z $HOST $PORT && break
    sleep 1
  done

  if nc -z $HOST $PORT; then
    if [ "$QUIET" -eq 0 ]; then
      echo "$HOST:$PORT is available after $(( (try - 1) * TIMEOUT + i )) seconds."
    fi
    sleep $POST_SUCCESS_WAIT  # Wait additional time after successful connection
    exit 0
  else
    if [ $try -lt $MAX_TRIES ]; then
      if [ "$QUIET" -eq 0 ]; then
        echo "Retry $try: $HOST:$PORT is still not available. Trying again in $WAIT_INTERVAL seconds..."
      fi
      sleep $WAIT_INTERVAL
    else
      if [ "$QUIET" -eq 0 ]; then
        echo "All retries failed. $HOST:$PORT is still not reachable."
      fi
      exit 1
    fi
  fi
done

exit 0
