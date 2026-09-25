#!/bin/bash
# Regenerate index.html — contact sheet of every competitor image in this folder.
cd "$(dirname "$0")"
{
echo '<!doctype html><meta charset=utf-8><title>Bear Necessities — Competitor Reference</title>'
echo '<style>body{background:#14110f;color:#e8e2d9;font:15px/1.5 -apple-system,sans-serif;margin:0;padding:32px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:38px 0 4px;color:#e0a049;border-bottom:1px solid #3a332c;padding-bottom:6px}
p.n{color:#9a9086;margin:0 0 14px;font-size:13px;max-width:70ch}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
figure{margin:0;background:#1f1b17;border-radius:6px;overflow:hidden}
img{width:100%;height:210px;object-fit:cover;display:block;cursor:zoom-in}
img.big{height:auto;object-fit:contain}
figcaption{font-size:11px;color:#8a8078;padding:6px 8px;word-break:break-all}</style>'
echo '<h1>Competitor reference — modular vehicle camp systems</h1>'
echo "<p class=n>Third-party product photography, collected $(date +%Y-%m-%d) for private design reference only. Copyright remains with each brand — do not reuse on the Bear Necessities website or in any published material. Click any image to expand. Regenerate with <code>./make-index.sh</code>.</p>"
for d in */; do
  b="${d%/}"; [ -z "$(ls -A "$b" 2>/dev/null)" ] && continue
  echo "<h2>$b</h2><p class=n>$(grep -A1 "^### $b" README.md 2>/dev/null | tail -1)</p><div class=g>"
  for f in "$b"/*; do
    case "$f" in *.jpg|*.jpeg|*.png|*.webp)
      echo "<figure><img src=\"$f\" onclick=\"this.classList.toggle('big')\"><figcaption>$(basename "$f")</figcaption></figure>";;
    esac
  done
  echo '</div>'
done
} > index.html
echo "wrote index.html ($(grep -c '<figure>' index.html) images)"
