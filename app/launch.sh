export PYTHONUNBUFFERED=1 
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/moondream_station" "$@"
exit $?