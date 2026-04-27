#!/usr/bin/env bash
set -euo pipefail

PLUGIN_NAME="krita_ai_metadata"
DESKTOP_FILE="${PLUGIN_NAME}.desktop"
OUT_ZIP="${PLUGIN_NAME}.zip"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "$PLUGIN_NAME" ]]; then
	echo "ERROR: Missing plugin folder: $PLUGIN_NAME/"
	exit 1
fi

if [[ ! -f "$DESKTOP_FILE" ]]; then
	echo "ERROR: Missing desktop file: $DESKTOP_FILE"
	exit 1
fi

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
	PYTHON_BIN="python"
else
	echo "ERROR: Python is required to build the plugin zip."
	exit 1
fi

rm -f "$OUT_ZIP"

"$PYTHON_BIN" - <<'PY'
import os
import zipfile

plugin_name = "krita_ai_metadata"
desktop_file = f"{plugin_name}.desktop"
out_zip = f"{plugin_name}.zip"

exclude_dirs = {
	".git",
	".idea",
	".vscode",
	"__pycache__",
	".pytest_cache",
	".mypy_cache",
	".ruff_cache",
	"build",
	"dist",
}

exclude_files = {
	out_zip,
}

def should_skip_dir(name: str) -> bool:
	return name in exclude_dirs

def should_skip_file(name: str) -> bool:
	if name in exclude_files:
		return True
	if name.endswith((".pyc", ".pyo", ".pyd", ".log", ".tmp", ".bak")):
		return True
	return False

with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
	zf.write(desktop_file, desktop_file)

	for root, dirs, files in os.walk(plugin_name):
		dirs[:] = [d for d in dirs if not should_skip_dir(d)]

		for filename in files:
			if should_skip_file(filename):
				continue

			path = os.path.join(root, filename)
			arcname = path.replace(os.sep, "/")
			zf.write(path, arcname)

print(f"Built {out_zip}")
print("ZIP root contains:")
print(f"- {plugin_name}/")
print(f"- {desktop_file}")
