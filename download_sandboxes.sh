#!/bin/bash

DEFAULT_MANIFEST_URL="https://downloads.sio2project.mimuw.edu.pl/sandboxes/Manifest"
DEFAULT_DOWNLOAD_DIR="sandboxes-download"
DEFAULT_WGET="wget"
QUIET=false
AGREE_LICENSE=false

echoerr() { echo "$@" 1>&2; }

usage() {
    echo "Usage: $0 [options] [sandbox1 sandbox2 ...]"
    echo ""
    echo "Options:"
    echo "  -m, --manifest URL       Specifies URL with the Manifest file listing available sandboxes (default: $DEFAULT_MANIFEST_URL)"
    echo "  -d, --download-dir DIR   Specify the download directory (default: $DEFAULT_DOWNLOAD_DIR)"
    echo "  -c, --cache-dir DIR   Load cached sandboxes from a local directory (default: None)"
    echo "  --wget PATH              Specify the wget binary to use (default: $DEFAULT_WGET)"
    echo "  -y, --yes                Enabling this options means that you agree to the license terms and conditions, so no license prompt will be displayed"
    echo "  -q, --quiet              Disables wget interactive progress bars"
    echo "  -h, --help               Display this help message"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -m|--manifest)
            MANIFEST_URL="$2"
            shift 2
            ;;
        -d|--download-dir)
            DOWNLOAD_DIR="$2"
            shift 2
            ;;
        -c|--cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        --wget)
            WGET_CMD="$2"
            shift 2
            ;;
        -y|--yes)
            AGREE_LICENSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        --)
            shift
            break
            ;;
        -*)
            echoerr "Unknown argument: $1"
            usage
            ;;
        *)
            break
            ;;
    esac
done

MANIFEST_URL="${MANIFEST_URL:-$DEFAULT_MANIFEST_URL}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$DEFAULT_DOWNLOAD_DIR}"
WGET_CMD="${WGET_CMD:-$DEFAULT_WGET}"

SANDBOXES=("$@")


if ! MANIFEST_CONTENT=$(curl -fsSL "$MANIFEST_URL"); then
    echoerr "Error: Unable to download manifest from $MANIFEST_URL"
    exit 1
fi

IFS=$'\n' read -d '' -r -a MANIFEST <<< "$MANIFEST_CONTENT"


BASE_URL=$(dirname "$MANIFEST_URL")/
LICENSE_URL="${BASE_URL}LICENSE"

LICENSE_CONTENT=$(curl -fsSL "$LICENSE_URL")
LICENSE_STATUS=$?

if [[ $LICENSE_STATUS -eq 0 ]]; then
    if ! $AGREE_LICENSE; then
        echoerr ""
        echoerr "The sandboxes are accompanied with a license:"
        echoerr "$LICENSE_CONTENT"
        while true; do
            read -rp "Do you accept the license? (yes/no): " yn
            case "$yn" in
                yes ) break;;
                no ) echoerr "License not accepted. Exiting..."; exit 1;;
                * ) echoerr 'Please enter either "yes" or "no".';;
            esac
        done
    fi
elif [[ $LICENSE_STATUS -ne 22 ]]; then
    echoerr "Error: Unable to download LICENSE from $LICENSE_URL"
    exit 1
fi

if [[ ${#SANDBOXES[@]} -eq 0 ]]; then
    SANDBOXES=("${MANIFEST[@]}")
fi


URLS=()
for SANDBOX in "${SANDBOXES[@]}"; do
    found=false
    for item in "${MANIFEST[@]}"; do
        if [[ "$item" == "$SANDBOX" ]]; then
            found=true
            break
        fi
    done

    if [[ $found == false ]]; then
        echoerr "Error: Sandbox '$SANDBOX' not available (not in Manifest)"
        exit 1
    fi

    echo "$SANDBOX";

    BASENAME="${SANDBOX}.tar.gz"

     if [[ -n "$CACHE_DIR" && -f "$CACHE_DIR/$BASENAME" ]]; then
        continue
    fi

    URL="${BASE_URL}${BASENAME}"
    URLS+=("$URL")
done

if [[ ! -d "$DOWNLOAD_DIR" ]]; then
    if ! mkdir -p "$DOWNLOAD_DIR"; then
        echoerr "Error: Unable to create download directory '$DOWNLOAD_DIR'"
        exit 1
    fi
fi

if ! command -v "$WGET_CMD" &> /dev/null; then
    echoerr "Error: '$WGET_CMD' is not installed or not in PATH."
    exit 1
fi

WGET_OPTIONS=("--no-check-certificate")
if $QUIET; then
    WGET_OPTIONS+=("-nv")
fi

for URL in "${URLS[@]}"; do
    BASENAME=$(basename "$URL")
    OUTPUT_PATH="$DOWNLOAD_DIR/$BASENAME"
    if ! "$WGET_CMD" "${WGET_OPTIONS[@]}" -O "$OUTPUT_PATH" "$URL"; then
        echoerr "Error: Failed to download $BASENAME"
        exit 1
    fi
done

exit 0
