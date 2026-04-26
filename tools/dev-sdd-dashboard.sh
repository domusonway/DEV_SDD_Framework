#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${ROOT_DIR}/.cache/dev_sdd"
LOG_FILE="${LOG_DIR}/dashboard-launch.log"
HTML_PATH="${ROOT_DIR}/docs/reports/dev-sdd-dashboard.html"

mkdir -p "${LOG_DIR}"

notify() {
  local message="$1"
  if command -v zenity >/dev/null 2>&1; then
    zenity --info --title="DEV SDD Dashboard" --text="${message}" >/dev/null 2>&1 || true
  elif command -v kdialog >/dev/null 2>&1; then
    kdialog --msgbox "${message}" >/dev/null 2>&1 || true
  elif command -v xmessage >/dev/null 2>&1; then
    xmessage "${message}" >/dev/null 2>&1 || true
  else
    printf '%s\n' "${message}"
  fi
}

open_file() {
  local target="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${target}" >/dev/null 2>&1 &
  elif command -v gio >/dev/null 2>&1; then
    gio open "${target}" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then
    open "${target}" >/dev/null 2>&1 &
  else
    python3 -m webbrowser "file://${target}" >/dev/null 2>&1 &
  fi
}

cd "${ROOT_DIR}" || exit 1

if python3 ".claude/tools/dev-sdd-dashboard/run.py" --task "double-click dashboard" --html "${HTML_PATH}" --json >"${LOG_FILE}" 2>&1; then
  open_file "${HTML_PATH}"
else
  notify "DEV SDD Dashboard 生成失败。日志：${LOG_FILE}"
  exit 1
fi
