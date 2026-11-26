#!/usr/bin/env python3
"""Pós-traduçêo (idempotente): canonical por idioma, hreflang x-default, og:*, banners por idioma."""
import re
from pathlib import Path
R = Path(__file__).resolve().parents[1] / 'guia'
BASE = 'https://inematds.github.io/robo-conversa/guia/'
for lang, p, url, ban in [('pt', R / 'index.html', BASE, 'banner.jpg'), ('en', R / 'en/index.html', BASE + 'en/', 'banner-en.jpg'),
                          ('es', R / 'es/index.html', BASE + 'es/', 'banner-es.jpg')]:
    s = p.read_text()
    s = re.sub(r'<link href="[^"]*" rel="canonical"/>', f'<link href="{url}" rel="canonical"/>', s)
    s = re.sub(r'<meta content="[^"]*" property="og:image"/>', f'<meta content="{BASE}assets/{ban}" property="og:image"/>', s)
    s = re.sub(r'\n*<link href="[^"]*" hreflang="[^"]*" rel="alternate"/>', '', s)
    alt = ''.join(f'<link href="{u}" hreflang="{h}" rel="alternate"/>' for h, u in
                  [('pt-BR', BASE), ('en', BASE + 'en/'), ('es', BASE + 'es/'), ('x-default', BASE)])
    s = s.replace(f'<link href="{url}" rel="canonical"/>', f'<link href="{url}" rel="canonical"/>' + alt, 1)
    t = re.search(r'<title>(.*?)</title>', s, re.S).group(1)
    d = re.search(r'<meta content="([^"]*)" name="description"/>', s).group(1)
    if 'property="og:title"' not in s:
        s = s.replace('<meta content="' + f'{BASE}assets/{ban}' + '" property="og:image"/>',
                      f'<meta content="{t}" property="og:title"/><meta content="{d}" property="og:description"/><meta content="{BASE}assets/{ban}" property="og:image"/>', 1)
    if lang != 'pt':
        s = s.replace('assets/banner.jpg', f'assets/{ban}').replace('assets/banner-grade.jpg', f'assets/banner-grade-{lang}.jpg')
    p.write_text(s)
    print(lang, 'ok', s.count('hreflang'), s.count('robo-caixa-fixa'))
