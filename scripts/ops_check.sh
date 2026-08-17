#!/usr/bin/env sh
set -eu

APP_URL="${APP_URL:-http://localhost:8000/health}"
EXPECTED_ENV="${EXPECTED_ENV:-}"
PORT="${PORT:-8000}"
PROCESS_PATTERN="${PROCESS_PATTERN:-uvicorn app.main:app}"
LOG_FILE="${LOG_FILE:-}"
FAILURES=0

info() {
  printf '[INFO] %s\n' "$1"
}

pass() {
  printf '[PASS] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

fail() {
  printf '[FAIL] %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

check_process() {
  if has_command pgrep; then
    if pgrep -f "$PROCESS_PATTERN" >/dev/null 2>&1; then
      pass "process is running: $PROCESS_PATTERN"
    else
      fail "process not found: $PROCESS_PATTERN"
    fi
  else
    warn "pgrep not available; skipping process check"
  fi
}

check_port() {
  if has_command ss; then
    if ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${PORT}$"; then
      pass "port is listening: $PORT"
    else
      fail "port is not listening: $PORT"
    fi
  elif has_command netstat; then
    if netstat -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)${PORT}$"; then
      pass "port is listening: $PORT"
    else
      fail "port is not listening: $PORT"
    fi
  else
    warn "ss/netstat not available; skipping port check"
  fi
}

check_resources() {
  if has_command df; then
    info "disk usage"
    df -h . | tail -n 1
  fi

  if has_command free; then
    info "memory usage"
    free -m | awk 'NR==1 || NR==2 {print}'
  else
    warn "free not available; skipping memory check"
  fi
}

check_health() {
  if has_command curl; then
    body="$(curl --fail --silent --show-error --max-time 5 "$APP_URL" || true)"
  elif has_command wget; then
    body="$(wget -q -T 5 -O - "$APP_URL" || true)"
  else
    warn "curl/wget not available; skipping health endpoint check"
    return
  fi

  if [ -z "$body" ]; then
    fail "health endpoint did not return a response: $APP_URL"
    return
  fi

  printf '%s\n' "$body" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' \
    && pass "health endpoint returned status ok" \
    || fail "health endpoint response is not healthy: $body"

  if [ -n "$EXPECTED_ENV" ]; then
    printf '%s\n' "$body" | grep -q "\"environment\"[[:space:]]*:[[:space:]]*\"$EXPECTED_ENV\"" \
      && pass "health endpoint environment matches: $EXPECTED_ENV" \
      || fail "health endpoint environment mismatch: expected $EXPECTED_ENV, got $body"
  fi
}

check_logs() {
  if [ -z "$LOG_FILE" ]; then
    warn "LOG_FILE is not set; skipping log tail"
    return
  fi

  if [ ! -f "$LOG_FILE" ]; then
    fail "log file not found: $LOG_FILE"
    return
  fi

  info "last 20 log lines from $LOG_FILE"
  tail -n 20 "$LOG_FILE"

  if tail -n 200 "$LOG_FILE" | grep -Eiq 'traceback|exception|error|critical'; then
    warn "recent logs contain error-like keywords"
  else
    pass "recent logs do not contain common error keywords"
  fi
}

info "CloudSec Copilot Linux operations check"
info "APP_URL=$APP_URL PORT=$PORT PROCESS_PATTERN=$PROCESS_PATTERN"

check_process
check_port
check_resources
check_health
check_logs

if [ "$FAILURES" -eq 0 ]; then
  pass "ops check completed"
  exit 0
fi

fail "ops check completed with $FAILURES failure(s)"
exit 1
