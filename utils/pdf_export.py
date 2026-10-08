"""
Conversion HTML → PDF avec Chrome/Chromium sans interface.

Même moteur que le bouton « Imprimer → Enregistrer en PDF » du navigateur :
le rendu (CSS @media print, @page A4, polices) est identique.
Sur Streamlit Cloud, Chromium est installé via packages.txt.
"""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


class PdfExportError(Exception):
    """Conversion PDF impossible (Chromium absent ou erreur de rendu)."""


_CANDIDATES = [
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def _find_browser() -> str:
    if os.getenv("CHROME_BIN"):
        return os.environ["CHROME_BIN"]
    for name in _CANDIDATES:
        path = shutil.which(name) or (name if os.path.exists(name) else None)
        if path:
            return path
    raise PdfExportError(
        "Chromium introuvable : ajoutez « chromium » dans packages.txt (Streamlit Cloud) "
        "ou installez Google Chrome (local)."
    )


def html_to_pdf(html: str, timeout: int = 120) -> bytes:
    """Rend le HTML (média print) et renvoie les octets du PDF."""
    browser = _find_browser()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "document.html"
        out = Path(tmp) / "document.pdf"
        if "@page" not in html:
            # Sans format déclaré, Chrome imprime en Lettre US : on force l'A4
            a4 = "<style>@page { size: A4; margin: 0; }</style>"
            html = html.replace("</head>", a4 + "</head>", 1) if "</head>" in html else a4 + html
        src.write_text(html, encoding="utf-8")
        cmd = [
            browser,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            # Laisse le temps aux polices et icônes (CDN) de se charger
            "--virtual-time-budget=15000",
            f"--user-data-dir={Path(tmp) / 'profile'}",
            f"--print-to-pdf={out}",
            src.as_uri(),
        ]
        # Chrome (surtout sur macOS) ne rend pas toujours la main après l'impression :
        # on attend que le PDF soit complètement écrit, puis on arrête le processus.
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        deadline = time.monotonic() + timeout
        last_size, stable_since = -1, None
        try:
            while time.monotonic() < deadline:
                exited = proc.poll() is not None
                size = out.stat().st_size if out.exists() else 0
                if size > 0 and size == last_size:
                    stable_since = stable_since or time.monotonic()
                    if exited or time.monotonic() - stable_since > 1.0:
                        break
                else:
                    stable_since = None
                last_size = size
                if exited and size == 0:
                    break
                time.sleep(0.25)
        finally:
            if proc.poll() is None:
                proc.kill()
            try:
                _, err = proc.communicate(timeout=5)
            except Exception:
                err = b""
        if not out.exists() or out.stat().st_size == 0:
            if time.monotonic() >= deadline:
                raise PdfExportError("La conversion PDF a pris trop de temps.")
            detail = (err or b"").decode("utf-8", errors="replace").strip().splitlines()[-3:]
            raise PdfExportError("Conversion PDF échouée. " + " | ".join(detail))
        data = out.read_bytes()
        if not data.startswith(b"%PDF"):
            raise PdfExportError("Le fichier produit n'est pas un PDF valide.")
        return data
