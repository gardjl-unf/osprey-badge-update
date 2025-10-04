#!/bin/sh
# runb.sh - wrapper used from JCL to run the badge updater
#
# Edit the variables below to set absolute paths on the z/OS host if you
# want the job to use non-default locations. If left empty, the script
# will fall back to the per-user default directory /u/<userid>/python_scripts
# and the default filenames students.json and directory1.html.

# Absolute overrides (set these to the full paths you want on the host)
STUDENTS_PATH_OVERRIDE="/u/s990061/python_scripts/students.json"   # e.g. /u/yourid/data/students.json
HTML_PATH_OVERRIDE="/u/s990061/public_html/directory1.html"       # e.g. /u/yourid/public_html/directory1.html

# --- below here the script computes final paths and runs the python script ---
SCRIPT_DIR="$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")"
PR="/u/$(id -un)/python_scripts"
PY="/usr/lpp/IBM/cyp/v3r8/pyz/bin/python3"
if [ ! -x "$PY" ]; then
    PY="$(which python3 2>/dev/null || echo /usr/bin/python3)"
fi

# Defaults (if not overridden)
STUDENTS_FILENAME="students.json"
HTML_FILENAME="directory1.html"

# Allow positional overrides (keeps backwards compatibility)
if [ "$#" -ge 1 ]; then
    STUDENTS_FILENAME="$1"
fi
if [ "$#" -ge 2 ]; then
    HTML_FILENAME="$2"
fi

# Apply absolute overrides if set
if [ -n "$STUDENTS_PATH_OVERRIDE" ]; then
    STUDENTS_PATH="$STUDENTS_PATH_OVERRIDE"
else
    case "$STUDENTS_FILENAME" in
        /*) STUDENTS_PATH="$STUDENTS_FILENAME" ;;
        *) STUDENTS_PATH="$PR/$STUDENTS_FILENAME" ;;
    esac
fi

if [ -n "$HTML_PATH_OVERRIDE" ]; then
    HTML_PATH="$HTML_PATH_OVERRIDE"
else
    case "$HTML_FILENAME" in
        /*) HTML_PATH="$HTML_FILENAME" ;;
        *) HTML_PATH="$PR/$HTML_FILENAME" ;;
    esac
fi

LOGDIR="/var/tmp"
if [ ! -d "$LOGDIR" ]; then
    LOGDIR="/tmp"
fi
USERLOGDIR="/u/$(id -un)/logs"
if [ -d "$USERLOGDIR" ]; then
    LOGDIR="$USERLOGDIR"
fi
LOGFILE="$LOGDIR/runb.$(id -un).$(date +%Y%m%d_%H%M%S).log"

# helper to emit messages to stdout, stderr and append to logfile
log() {
    # preserve arguments exactly
    echo "$@"
    echo "$@" >&2
    # try to append to logfile but don't fail the script if we can't
    if [ -n "$LOGFILE" ]; then
        mkdir -p "$(dirname "$LOGFILE")" 2>/dev/null || true
        echo "$(date +%Y-%m-%dT%H:%M:%S) $@" >>"$LOGFILE" 2>/dev/null || true
    fi
}

log "runb.sh: PY=$PY"
if [ ! -x "$PY" ]; then
    log "ERROR: Python interpreter not found or not executable: $PY"
    exit 12
fi

log "runb.sh: PR=$PR"
if [ ! -d "$PR" ]; then
    log "ERROR: Scripts directory not found: $PR"
    exit 13
fi

UPDATER="$PR/update_directory_badges.py"
if [ ! -f "$UPDATER" ]; then
    log "ERROR: updater script not found: $UPDATER"
    exit 14
fi

log "runb.sh: STUDENTS_PATH=$STUDENTS_PATH"
if [ ! -f "$STUDENTS_PATH" ]; then
    log "ERROR: students json file not found: $STUDENTS_PATH"
    exit 15
fi

HTML_DIR="$(dirname "$HTML_PATH")"
log "runb.sh: HTML_PATH=$HTML_PATH (dir $HTML_DIR)"
if [ ! -d "$HTML_DIR" ]; then
    log "ERROR: target HTML directory not found: $HTML_DIR"
    exit 16
fi

log "runb.sh: Logging to $LOGFILE"

exec "$PY" "$UPDATER" "$STUDENTS_PATH" "$HTML_PATH"
