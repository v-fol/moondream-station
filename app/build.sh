#!/usr/bin/env bash
set -euo pipefail

TYPE=${1:-}            # inference | hypervisor | cli | dev
PLATFORM=${2:-ubuntu}  # mac | ubuntu  (default ubuntu)

##############################################################################
# builders
##############################################################################
build_inference() {
    local PYI_ARGS="--onefile"
    local NAME="inference_bootstrap"
    local DIST_DIR="../output/inference_bootstrap"
    local BOOTSTRAP="../app/inference_client/bootstrap.py"
    local SRC_DIR="../app/inference_client"
    local FILES=(main.py model_service.py requirements.txt)

    echo "Building 'inference'..."
    rm -rf "$DIST_DIR"; mkdir -p "$DIST_DIR"

    pyinstaller $PYI_ARGS \
        --hidden-import=urllib.request \
        --hidden-import=zipfile \
        --hidden-import=pyvips \
        --name "$NAME" \
        --distpath "$DIST_DIR" \
        "$BOOTSTRAP"

    for f in "${FILES[@]}"; do
        cp "$SRC_DIR/$f" "$DIST_DIR"
    done
    echo "✔ inference → $DIST_DIR"
}

build_hypervisor() {
    local PYI_ARGS
    if [[ "$PLATFORM" = "mac" ]]; then
        PYI_ARGS="--windowed"   # .app bundle
    elif [[ "$PLATFORM" = "ubuntu" ]]; then
        PYI_ARGS="--onefile"
    else
        echo "Unknown platform '$PLATFORM' (mac|ubuntu)" >&2; exit 1
    fi

    local NAME="moondream_station"
    local DIST_DIR="../output/moondream_station"
    local SUP_DIR="../output/moondream-station-files"
    local BOOTSTRAP="../app/hypervisor/bootstrap.py"
    local SRC_DIR="../app/hypervisor"
    local FILES=(
        hypervisor_server.py hypervisor.py inferencevisor.py requirements.txt
        manifest.py config.py misc.py update_bootstrap.sh clivisor.py
        display_utils.py
    )

    echo "Building 'hypervisor' for $PLATFORM..."
    rm -rf "$DIST_DIR" "$SUP_DIR"; mkdir -p "$DIST_DIR" "$SUP_DIR"

    pyinstaller $PYI_ARGS \
        --hidden-import=urllib.request \
        --hidden-import=zipfile \
        --name "$NAME" \
        --distpath "$DIST_DIR" \
        "$BOOTSTRAP"

    for f in "${FILES[@]}"; do
        cp "$SRC_DIR/$f" "$SUP_DIR/"
    done
    tar -czf "$DIST_DIR/hypervisor.tar.gz" -C "$SUP_DIR" .
    echo "✔ hypervisor → $DIST_DIR"
}

build_cli() {
    local NAME="moondream-cli"
    local DIST_DIR="../output/moondream-cli"
    local SRC_DIR="../app/moondream_cli"

    echo "Building 'cli'..."
    rm -rf "$DIST_DIR"; mkdir -p "$DIST_DIR"
    cp -r "$SRC_DIR" "$DIST_DIR/"
    tar -czf "../output/moondream-cli.tar.gz" -C "$DIST_DIR" moondream_cli
    echo "✔ cli → $DIST_DIR"
}

##############################################################################
# dev sandbox
##############################################################################
prepare_dev() {
    build_cli
    build_inference
    build_hypervisor

    local DEV_DIR
    if [[ "$PLATFORM" = "mac" ]]; then
        DEV_DIR="$HOME/Library/MoondreamStation"
    elif [[ "$PLATFORM" = "ubuntu" ]]; then
        DEV_DIR="$HOME/.local/share/MoondreamStation"
    else
        echo "Unknown platform '$PLATFORM' (mac|ubuntu)" >&2; exit 1
    fi

    mkdir -p "$DEV_DIR/inference/v0.0.1"

    # copy hypervisor supplements
    local HYP_SRC="../output/moondream-station-files"
    local HYP_FILES=(
        clivisor.py config.py display_utils.py hypervisor_server.py hypervisor.py
        inferencevisor.py manifest.py misc.py
    )
    for f in "${HYP_FILES[@]}"; do
        cp "$HYP_SRC/$f" "$DEV_DIR/"
    done

    # copy CLI dir
    cp -r "../output/moondream-cli/moondream_cli" "$DEV_DIR/"

    # copy inference build
    cp -r "../output/inference_bootstrap" "$DEV_DIR/inference/v0.0.1/"

    echo "✔ dev sandbox ready → $DEV_DIR"
}

##############################################################################
# dispatch
##############################################################################
case "$TYPE" in
    inference)   build_inference   ;;
    hypervisor)  build_hypervisor  ;;
    cli)         build_cli         ;;
    dev)         prepare_dev       ;;
    *)
        echo "Usage: $0 <inference|hypervisor|cli|dev> [platform]" >&2
        exit 1
        ;;
esac