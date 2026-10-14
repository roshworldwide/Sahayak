"""Build the whole phone app as ONE self-contained HTML file: dist/Sahayak.html.

Everything the stand-alone site needs is inside it: the app, its styles and icon font, the on-phone checker and
benefits engine, the signed packs (checked against their signatures first, by build_tryit), the game's cards and all
23 display languages. It needs no server and no internet: open it by double-clicking, from a USB stick, or in a chat
preview. Each fetch the app makes for one of its own files is answered from inside the page.

What it cannot do, as the stand-alone site cannot: voice input, screenshot reading, the agent queue. On a file:// page
there is no service worker, and a browser may keep nothing between visits (the game's score and the chosen
language then start fresh).

  python scripts/build_single_html.py [out_file]     (default dist/Sahayak.html)
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ("mic.js", "checker.js", "navigator.js", "i18n.js", "app.js")


def data_uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def safe_js(text: str) -> str:
    """Script text that cannot end its own <script> element early."""
    return re.sub(r"</(script)", r"<\\/\1", text, flags=re.I)


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "Sahayak.html"
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_tryit.py"), str(site)], check=True)
        app = site / "app"
        html = (site / "index.html").read_text(encoding="utf-8")

        # the files the app fetches by itself, served from inside the page
        files = {f"app/{n}": (app / n).read_text(encoding="utf-8") for n in ("game.json", "story.json")}
        for f in sorted((app / "i18n").glob("*.json")):
            files[f"app/i18n/{f.name}"] = f.read_text(encoding="utf-8")
        for f in sorted((site / "phone-packs").glob("*.json")):
            files[f"phone-packs/{f.name}"] = f.read_text(encoding="utf-8")
        shim = ("window.__SAHAYAK_FILES__ = " + json.dumps(files, ensure_ascii=False) + ";\n" + """
(function () {
  var files = window.__SAHAYAK_FILES__, real = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function (input, init) {
    var url = typeof input === "string" ? input : (input && input.url) || "";
    var m = url.split(/[?#]/)[0].match(/(?:^|\\/)((?:app|phone-packs)\\/.+)$/);
    var key = m ? m[1].replace(/^app\\/app\\//, "app/") : "";
    if (key && Object.prototype.hasOwnProperty.call(files, key)) {
      return Promise.resolve(new Response(files[key], { status: 200, headers: { "Content-Type": "application/json" } }));
    }
    if (key) return Promise.resolve(new Response("", { status: 404 }));
    return real ? real(input, init) : Promise.reject(new TypeError("offline"));
  };
})();
""")

        css = (app / "app.css").read_text(encoding="utf-8")
        css = css.replace("url(fonts/symbols.woff2)", f"url({data_uri(app / 'fonts' / 'symbols.woff2', 'font/woff2')})")
        html = html.replace('<link rel="stylesheet" href="app/app.css">', f"<style>\n{css}\n</style>")
        html = re.sub(r'<link rel="(?:manifest|preload|apple-touch-icon)"[^>]*>\n?', "", html)
        html = html.replace('href="app/icons/icon.svg"', f'href="{data_uri(app / "icons" / "icon.svg", "image/svg+xml")}"')

        scripts = "".join(f"<script>\n{safe_js((app / name).read_text(encoding='utf-8'))}\n</script>\n" for name in SCRIPTS)
        html = re.sub(r'<script src="app/[^"]+" defer></script>\n?', "", html)
        html = html.replace("</body>", f"<script>\n{safe_js(shim)}\n</script>\n{scripts}</body>")
        leftover = re.findall(r'(?:src|href)="app/[^"]*"', html)
        if leftover:
            raise SystemExit(f"still points at separate files: {leftover}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"{out}: one file, {out.stat().st_size / 1e6:.2f} MB, {len(files)} files inside")


if __name__ == "__main__":
    main()
