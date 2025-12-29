# CertiSense — demo landing page

This folder contains a static demo landing page for the CertiSense prototype. It's intentionally self-contained (HTML/CSS/JS) and simulates a ChatGPT-like assistant for presenting the tool during demos.

Files
- `index.html` — main page
- `styles.css` — styling
- `script.js` — simulated chat interactions and file preview

How to open
1. Open the folder in your browser or from your file manager.
2. On Windows you can double-click `index.html`, or open PowerShell and run:

```powershell
Start-Process "${PWD}\demo_landing_page\index.html"
```

Notes
- This is a client-only demo. No model or external API calls are made; responses are simulated for presentation.
- You can upload small text/PDF files; the demo reads the first chunk and shows a preview. PDF binary preview may be noisy — best to use plain text or exported text versions for demos.
