"""Apply the catalog identity to HTML from all of the site's page generators."""
from pathlib import Path
import hashlib
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
LINKS = (("/#catalog", "APIs"), ("/#tools", "Tools"), ("/#roadmap", "Roadmap"), ("/pricing/", "Pricing"))


POLICIES = (("/terms/", "Terms of Service"), ("/privacy/", "Privacy Policy"),
            ("/refund/", "Refund Policy"), ("/legal/", "Licences and contact"))


def shell(body, route):
    policies = "".join(f'<a href="{url}">{label}</a>' for url, label in POLICIES)
    policy_menu = ('<details class="bw-policies"><summary>Policies</summary>'
                   f'<div>{policies}</div></details>')
    links = "".join(f'<a href="{url}"' + (' aria-current="page"' if route == url else '') +
                    f'>{label}</a>' for url, label in LINKS)
    header = (f'<header class="bw-header"><a class="bw-logo" href="/">BlvkWare<b>.</b></a>'
              f'<nav class="bw-desktop" aria-label="Main">{links}{policy_menu}</nav>'
              f'<details><summary>Menu</summary><nav aria-label="Main">{links}{policies}</nav></details></header>')
    if '<header class="bw-header">' in body:
        return re.sub(r'<header class="bw-header">.*?</header>', lambda _: header, body, count=1, flags=re.S)
    for pattern in (r'<header class="sitebar"[^>]*>.*?</header>',
                    r'<header><a class="logo".*?</header>',
                    r'<nav><a class="brand" href="/">BLVKWARE</a>.*?</nav>'):
        if re.search(pattern, body, re.S):
            body = re.sub(pattern, lambda _: header, body, count=1, flags=re.S)
            break
    else:
        body = re.sub(r'(<body\b[^>]*>)', lambda m: m[0] + header, body, count=1)
    if '/assets/fonts/fonts.css' not in body:
        body = body.replace('</head>', '<link rel="stylesheet" href="/assets/fonts/fonts.css"></head>', 1)
    if 'href="/assets/site-shell.css' in body:
        return body
    return body.replace('</head>', '<link rel="stylesheet" href="/assets/site-shell.css"></head>', 1)


def publish(retired, output):
    shutil.copyfile(SOURCE / "site-shell.css", output / "assets/site-shell.css")
    css_version = hashlib.sha256((SOURCE / "site-shell.css").read_bytes()).hexdigest()[:12]
    for route in (*retired, 'hire'):
        path = output / route / 'index.html'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text((SOURCE / 'retired.html').read_text())
    for slug, source in (("hallux/checkout", "hallux-checkout.html"), ("docs/payment", "payment-public.html")):
        shutil.copyfile(SOURCE / source, output / slug / "index.html")
    for path in output.rglob('*.html'):
        page = path.read_text()
        route = '/' + str(path.parent.relative_to(output)).strip('.') + '/'
        if 'http-equiv="refresh"' in page[:1500].lower():
            continue
        if route == '/docs/hallux-spec/':
            page = re.sub(r'<h3>The ladder</h3>.*?<h3>Settlement</h3>',
                          '<h3>Usage pricing</h3><p>Each identifier costs one prepaid credit. '
                          '<a href="/pricing/#credits">Compare credit packs</a>.</p><h3>Settlement</h3>', page, flags=re.S)
        page = re.sub(r'href="/assets/site-shell\.css(?:\?v=[a-f0-9]+)?"',
                      f'href="/assets/site-shell.css?v={css_version}"', shell(page, route))
        path.write_text(page)
    for path in (output / 'pricing/embedded.txt', output / 'samples/blvkware-sample-kit-follow-up-agent.zip'):
        path.unlink(missing_ok=True)
