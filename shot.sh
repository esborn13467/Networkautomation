#!/usr/bin/env bash
# Takes a real screenshot of a terminal window running one command, for the report.
#   ./shot.sh <name> "<command>" [wait_seconds] [columns] [rows]
# Opens a FULL-SCREEN xfce4-terminal in the project folder, shows "$ <command>", runs it,
# waits, screenshots the WHOLE SCREEN to results/screens/<name>.png, then closes the terminal.
cd "$(dirname "$0")"
NAME=$1; CMD=$2; WAIT=${3:-6}
OUT="results/screens"; mkdir -p "$OUT"
TITLE="zt-shot-$NAME-$$"
setsid -f xfce4-terminal --disable-server --title="$TITLE" --fullscreen --font="DejaVu Sans Mono 15" \
  --working-directory="$PWD" -x bash -c "printf '\$ %s\n' \"$CMD\"; $CMD; sleep 3600" >/dev/null 2>&1
for i in $(seq 1 20); do                       # wait for the window to appear
  WID=$(xdotool search --name "$TITLE" 2>/dev/null | head -1); [ -n "$WID" ] && break; sleep 0.5
done
[ -z "$WID" ] && { echo "window did not open"; exit 1; }
xdotool windowactivate "$WID" 2>/dev/null
sleep "$WAIT"                                   # let the command finish printing
import -window root "$OUT/$NAME.png"
xdotool windowclose "$WID" 2>/dev/null || xdotool windowkill "$WID"
echo "saved $OUT/$NAME.png"
