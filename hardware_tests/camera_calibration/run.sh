#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# UR5e wrist D405:
# CALIBRATION_CONFIG="${CALIBRATION_CONFIG:-configs/ur5e_d405.yaml}"

# UR5e fixed Azure Kinect:
# CALIBRATION_CONFIG="${CALIBRATION_CONFIG:-configs/ur5e_kinect.yaml}"

# ABB GoFa wrist D405:
CALIBRATION_CONFIG="${CALIBRATION_CONFIG:-configs/abb_gofa_d405.yaml}"

# ABB GoFa wrist DFK33UX252:
# CALIBRATION_CONFIG="${CALIBRATION_CONFIG:-configs/abb_gofa_dfk.yaml}"

# ABB GoFa fixed D455:
# CALIBRATION_CONFIG="${CALIBRATION_CONFIG:-configs/abb_gofa_d455.yaml}"

uv_sync_args_for_config() {
    local config_path="$1"
    local args=()

    if grep -q "backend: abb_rws" "$config_path"; then
        args+=(--extra abb)
    fi
    if grep -q "backend: ur_rtde" "$config_path"; then
        args+=(--extra ur)
    fi
    if grep -q "backend: realsense_local" "$config_path"; then
        args+=(--extra realsense)
    fi
    if grep -q "backend: azure_kinect" "$config_path"; then
        args+=(--extra azure-kinect)
    fi

    printf '%s\n' "${args[@]}"
}

USE_UV=0
if command -v uv >/dev/null 2>&1; then
    USE_UV=1
    if [ ! -d ".venv" ]; then
        mapfile -t UV_SYNC_ARGS < <(uv_sync_args_for_config "$CALIBRATION_CONFIG")
        echo "No local virtual environment found. Bootstrapping it with 'uv sync ${UV_SYNC_ARGS[*]}'."
        uv sync "${UV_SYNC_ARGS[@]}"
    fi
elif [ ! -x ".venv/bin/python" ]; then
    cat <<'EOF'
uv is not installed and no local .venv was found.

Install uv and run a workstation-specific sync command, for example:
  uv sync --extra abb --extra realsense

Or create a local virtual environment manually and install the project plus notebook extras.
EOF
    exit 1
fi

run_python() {
    if [ "$USE_UV" -eq 1 ]; then
        uv run "$@"
    else
        .venv/bin/python "$@"
    fi
}

sleep 1
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

run_python src/check_environment.py
run_python src/main.py --config "$CALIBRATION_CONFIG"
