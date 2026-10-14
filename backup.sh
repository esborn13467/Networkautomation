#!/usr/bin/env bash
# Mirror the project to the Desktop backup folder. Runs automatically after every git commit.
# Files are only added or updated in the backup, never deleted from it.
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Desktop/zt-project-backup"
mkdir -p "$DEST"
rsync -a --exclude __pycache__ --exclude 'clab-zt/' "$SRC/" "$DEST/" 2>/dev/null
rsync -a "$SRC/clab-zt/" "$DEST/clab-zt/" 2>/dev/null   # root-owned lab files: copy what is readable
date '+%Y-%m-%d %H:%M:%S' > "$DEST/LAST_BACKUP.txt"
echo "backup updated -> $DEST"
