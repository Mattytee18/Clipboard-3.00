# Clipboard Manager

Text snippets with categories, search and drag-to-reorder — for Windows, Mac and iPhone.

| File | What it is |
|---|---|
| `windows.pyw` | Windows app |
| `mac.py` | Mac app |
| `index.html` | Phone / web version (open in Safari → Share → Add to Home Screen) |
| `clipboard_items.json`, `clipboard_categories.json` | Starter snippets bundled into the Mac app |
| `icon.ico`, `icon.icns`, `icon.png` | App icons |

## Getting the built apps

GitHub builds both apps automatically (see `.github/workflows/build.yml`).

1. Open the **Actions** tab and click the latest **Build apps** run.
2. Scroll to **Artifacts** and download:
   - `ClipboardManager-windows` — contains `Clipboard Manager.exe`
   - `ClipboardManager-mac-apple-silicon` — for M1/M2/M3/M4 Macs
   - `ClipboardManager-mac-intel` — for older Intel Macs

To publish a proper download page, push a version tag:

```
git tag v1.0.0
git push origin v1.0.0
```

The files then appear under **Releases**.

You can also start a build by hand: **Actions → Build apps → Run workflow**.

## First launch

The apps aren't code-signed, so both systems warn the first time:

- **Windows:** SmartScreen says "Windows protected your PC" → **More info → Run anyway**.
- **Mac:** unzip, drag *Clipboard Manager* to Applications, then **right-click → Open → Open**.
  If macOS says the app "is damaged", run this once in Terminal:
  `xattr -cr "/Applications/Clipboard Manager.app"`

## Where data is saved

- **Windows:** next to `Clipboard Manager.exe` (keep the .exe in its own folder).
- **Mac:** `~/Library/Application Support/ClipboardManager/`

## Running from source

```
pip install -r requirements.txt
python windows.pyw      # or: python3 mac.py
```
