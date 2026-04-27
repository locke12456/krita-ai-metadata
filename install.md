# Install Guide

This guide explains how to test, build, and install the Krita AI Metadata plugin.

## 1. Run tests

Before building the plugin package, run the test suite from the repository root.

### Linux / macOS

    python3 -m pytest

### Windows PowerShell

    python -m pytest

### Windows Command Prompt

    python -m pytest

If `pytest` is not installed, install it first:

    python -m pip install pytest

---

## 2. Run build

The build script creates a Krita-compatible plugin ZIP package:

    krita_ai_metadata.zip

The ZIP package should contain:

    krita_ai_metadata.zip
    ├── krita_ai_metadata/
    └── krita_ai_metadata.desktop

### Linux / macOS

    chmod +x build.sh
    ./build.sh

### Windows PowerShell

    .\build.ps1

If PowerShell blocks the script, run:

    powershell -ExecutionPolicy Bypass -File .\build.ps1

### Windows Command Prompt

    build.bat

After the build finishes, confirm that this file exists:

    krita_ai_metadata.zip

---

## 3. Install package

You can install the plugin package directly from Krita.

### Install from ZIP

1. Open Krita.
2. Go to:

        Tools → Scripts → Import Python Plugin from File...

3. Select:

        krita_ai_metadata.zip

4. Restart Krita.
5. Enable the plugin if needed:

        Settings → Configure Krita → Python Plugin Manager

6. Restart Krita again if Krita asks you to.

---

## Manual installation

If ZIP import does not work, install manually.

1. Open Krita.
2. Go to:

        Settings → Manage Resources → Open Resource Folder

3. Open or create the `pykrita` folder.
4. Copy these items into `pykrita`:

        krita_ai_metadata/
        krita_ai_metadata.desktop

5. Restart Krita.
6. Enable the plugin from:

        Settings → Configure Krita → Python Plugin Manager

7. Restart Krita again if needed.

---

## Release package

For GitHub releases, upload this file as the release asset:

    krita_ai_metadata.zip

Users should download this ZIP file and install it through Krita's Python plugin importer.