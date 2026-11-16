# -*- coding: utf-8 -*-
"""Fetch one month's articles from palakneeti.in and turn them into the
   structured form the layout needs.   usage: fetchparse.py <issue-key>"""
import json, os, re, ssl, sys, time, urllib.request, urllib.parse, urllib.error
from bs4 import BeautifulSoup, NavigableString
from issues import resolve, find_category, is_month_index

BASE = os.path.dirname(os.path.abspath(__file__))
# Set when run as a script. Left as None when this module is imported purely
# for its parsing helpers (see authors.py), which also disables image saving.
KEY = CFG = IDIR = IMGDIR = None

# ── fetch ───────────────────────────────────────────────────────────────
# A bare "Mozilla/5.0" from a datacenter IP is exactly what a WAF blocks, so
# ask the way a browser would.
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/126.0.0.0 Safari/537.36'),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-GB,en;q=0.9,mr;q=0.8',
    'Referer': 'https://palakneeti.in/',
}


BLOCKED = (
    'The site\'s bot protection (Imunify360) refused this request.\n'
    '   It blocks datacenter IP addresses, which is what a GitHub runner uses.\n'
    '   It is intermittent, so trying again in a few minutes often works.\n'
    '   For a permanent fix, ask whoever hosts palakneeti.in to allow either\n'
    '   the GitHub Actions IP ranges or this tool\'s User-Agent.')


CERT = (
    "palakneeti.in's security certificate is not valid for that name.\n"
    '   This is nothing to do with the tool, this repository, or your access to\n'
    '   it — the certificate is served by whoever hosts palakneeti.in, and only\n'
    '   they can renew it. Open https://palakneeti.in in a browser and you will\n'
    '   see the same warning. Retrying will not clear it.')

DOWN = (
    'palakneeti.in answered, but with a server error and no content, so there\n'
    '   is nothing to read. Open https://palakneeti.in in a browser: if the site\n'
    '   is down or being worked on, the build can only wait for it to come back.\n'
    '   Again, this is the website, not the tool or your access.')


def fetch_json(url, attempts=6):
    """Fetch JSON, retrying a bot-protection block rather than losing the run."""
    last = ''
    for n in range(1, attempts + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                ctype = r.headers.get('Content-Type', '?')
            break
        except urllib.error.HTTPError as e:
            body = e.read()[:400].decode('utf-8', 'replace')
            last = f'HTTP {e.code} {e.reason}\n   {body}'
            transient = e.code in (403, 429, 500, 502, 503, 504)
        except urllib.error.URLError as e:
            # A bad certificate is not going to fix itself in 4 minutes, and
            # calling it "blocked" sends people hunting for a bot-protection
            # problem they do not have.
            if isinstance(e.reason, ssl.SSLError):
                raise SystemExit(f'!! {url}\n   {e.reason}\n   {CERT}')
            last, transient = f'could not connect: {e.reason}', True
        if n == attempts or not transient:
            hint = ''
            if 'Imunify360' in last:
                hint = '\n   ' + BLOCKED
            elif re.match(r'HTTP 5\d\d', last):
                hint = '\n   ' + DOWN
            raise SystemExit(f'!! {url}\n   {last}{hint}')
        wait = 5 * n * n                      # 5s → 125s, ~4 min in total
        print(f'   attempt {n} of {attempts - 1} failed '
              f'({last.splitlines()[0]}) — retrying in {wait}s', flush=True)
        time.sleep(wait)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        head = raw[:400].decode('utf-8', 'replace').replace('\n', ' ')
        raise SystemExit(
            f'!! {url}\n   returned {ctype}, not JSON ({len(raw)} bytes).\n'
            f'   The site may be blocking this request. First 400 bytes:\n'
            f'   {head}')


# ── html -> blocks ──────────────────────────────────────────────────────
def inline(el):
    runs = []

    def walk(node, bold=False, ital=False, href=None):
        for ch in node.children:
            if isinstance(ch, NavigableString):
                t = str(ch).replace('\xa0', ' ')
                if t:
                    runs.append({'t': t, 'b': bold, 'i': ital, 'href': href})
            else:
                if ch.name == 'br':
                    runs.append({'t': '\n', 'b': bold, 'i': ital, 'href': None})
                    continue
                walk(ch,
                     bold or ch.name in ('strong', 'b'),
                     ital or ch.name in ('em', 'i'),
                     ch['href'] if ch.name == 'a' and ch.get('href') else href)

    walk(el)
    merged = []
    for r in runs:
        if (merged and merged[-1]['b'] == r['b'] and merged[-1]['i'] == r['i']
                and merged[-1]['href'] == r['href']):
            merged[-1]['t'] += r['t']
        else:
            merged.append(dict(r))
    for r in merged:
        r['t'] = re.sub(r'[ \t]+', ' ', r['t'])
    while merged and not merged[0]['t'].strip():
        merged.pop(0)
    while merged and not merged[-1]['t'].strip():
        merged.pop()
    return merged


def plain(runs):
    return ''.join(r['t'] for r in runs).strip()


def to_blocks(html_src):
    soup = BeautifulSoup(html_src, 'html.parser')
    for junk in soup.select('.gsp_post_data'):
        junk.decompose()
    blocks = []
    for el in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p',
                             'figure', 'blockquote', 'ul', 'ol']):
        if el.find_parent(['blockquote', 'figure']):
            continue
        if el.name == 'figure':
            img = el.find('img')
            if not img:
                continue
            fn = fetch_image(img.get('src', ''))
            cap = el.find('figcaption')
            if fn or img.get('src'):
                blocks.append({'type': 'image', 'file': fn,
                               'src': img.get('src', ''),
                               'w': img.get('width'), 'h': img.get('height'),
                               'caption': cap.get_text(' ', strip=True) if cap else ''})
        elif el.name == 'blockquote':
            paras = [p for p in (inline(x) for x in el.find_all('p')) if plain(p)]
            if paras:
                blocks.append({'type': 'quote', 'paras': paras})
        elif el.name in ('ul', 'ol'):
            items = [i for i in (inline(li) for li in el.find_all('li', recursive=False))
                     if plain(i)]
            if items:
                blocks.append({'type': 'list', 'ordered': el.name == 'ol', 'items': items})
        elif el.name.startswith('h'):
            r = inline(el)
            if plain(r):
                blocks.append({'type': 'head', 'level': int(el.name[1]), 'runs': r})
        else:
            r = inline(el)
            if plain(r):
                blocks.append({'type': 'para', 'runs': r})
    return blocks


# ── blocks -> layout roles ──────────────────────────────────────────────
# A comma where the dot belongs is a typing slip on the site, not a different
# address — a comma cannot appear in a domain. Accept it, then repair it, or
# the author card silently disappears (dr.kasturi1004@gmail,com did exactly
# that to two articles).
EMAIL = re.compile(r'^[\w.\-+]+@[\w.\-]+[.,]\w+$')


def fix_email(t):
    return t.replace(',', '.')


def normalize(title, slug, blocks, post):
    b, n = blocks, len(blocks)

    email_i = None
    for i in range(n - 1, max(n - 12, -1), -1):
        # some articles style the address as a heading, not a paragraph
        if b[i]['type'] in ('para', 'head') and EMAIL.match(plain(b[i]['runs'])):
            email_i = i
            break

    tail, appendix, trailing_credit = None, [], None
    body_end = n

    if email_i is not None:
        # the author photo usually sits just above the email, but some
        # articles put it just below — look both ways
        photo_i = next((j for j in range(email_i - 1, max(email_i - 4, -1), -1)
                        if b[j]['type'] == 'image'), None)
        if photo_i is None:
            photo_i = next((j for j in range(email_i + 1, min(email_i + 4, n))
                            if b[j]['type'] == 'image'), None)
        start = photo_i if (photo_i is not None and photo_i < email_i) else email_i
        name_i = next((j for j in range(start - 1, max(start - 3, -1), -1)
                       if b[j]['type'] == 'para' and len(plain(b[j]['runs'])) < 60), None)

        bio, k = [], email_i + 1
        while k < n and (b[k]['type'] in ('para', 'head') or k == photo_i):
            if k == photo_i:          # the author photo, already accounted for
                k += 1
                continue
            t = plain(b[k]['runs'])
            if t.startswith('सौजन्य') or t.startswith('संदर्भ'):
                break
            bio.append(t)
            k += 1
        if k < n and b[k]['type'] in ('para', 'head') and plain(b[k]['runs']).startswith('सौजन्य'):
            trailing_credit = plain(b[k]['runs'])
            k += 1

        raw_name = plain(b[name_i]['runs']) if name_i is not None else ''
        role = None
        m = re.match(r'^(अनुवाद|शब्दांकन|छायाचित्र[े]?)\s*[:：]\s*(.+)$', raw_name)
        if m:
            role, raw_name = m.group(1), m.group(2).strip()

        tail = {'role': role, 'name': raw_name,
                'email': fix_email(plain(b[email_i]['runs'])),
                'photo': b[photo_i]['file'] if photo_i is not None else None,
                'photo_src': b[photo_i].get('src') if photo_i is not None else None,
                'bio': ' '.join(bio).strip()}
        body_end = name_i if name_i is not None else (
            photo_i if photo_i is not None else email_i)
        appendix = [x for x in b[k:]
                    if x['type'] in ('quote', 'list', 'para', 'head', 'image')]

    head = b[:body_end]
    # Scan the opening blocks for a section label and a byline. An article may
    # lead with an illustration, so look past images rather than stopping at
    # them — and only drop the blocks actually taken, so the image survives.
    kicker, byline, bi, seen = None, [], 0, set()
    while bi < len(head):
        blk = head[bi]
        if blk['type'] == 'image':
            bi += 1
            continue
        if blk['type'] == 'head' and blk['level'] <= 3 and kicker is None and bi <= 1:
            t = plain(blk['runs'])
            if tail and t.rstrip(' :') == tail['name']:
                byline.append(t)
            else:
                kicker = t
            seen.add(bi)
            bi += 1
            continue
        if blk['type'] == 'para':
            t = plain(blk['runs'])
            is_name = len(t) < 55 and not t.endswith(('.', '?', '!', '…'))
            if (is_name and len(byline) < 2) or t.startswith(('अनुवाद', 'शब्दांकन', 'छायाचित्र')):
                byline.append(t)
                seen.add(bi)
                bi += 1
                continue
        break

    body = [x for i, x in enumerate(head) if i not in seen]
    if tail and body and body[-1]['type'] == 'para' and plain(body[-1]['runs']) == tail['name']:
        body = body[:-1]
    if not byline and tail and tail['name']:
        byline = [(tail['role'] + ' : ' + tail['name']) if tail.get('role') else tail['name']]

    return {'id': post['id'], 'slug': slug, 'title': title, 'link': post['link'],
            'kicker': kicker, 'byline': byline, 'body': body,
            'tail': tail, 'credit': trailing_credit, 'appendix': appendix}


def setup(key):
    """Prepare the per-run paths and resolve the month's category."""
    global KEY, CFG, IDIR, IMGDIR
    KEY, CFG = key, resolve(key)
    IDIR = os.path.join(BASE, 'data', key)
    IMGDIR = os.path.join(BASE, 'build', 'images', key)
    os.makedirs(IDIR, exist_ok=True)
    os.makedirs(IMGDIR, exist_ok=True)
    CAT = CFG.get('category')
    if not CAT:
        found = find_category(KEY, fetch_json)
        if not found:
            raise SystemExit(
                f'!! no WordPress category found for {KEY} ({CFG["month_en"]}).\n'
                f'   Either the month is not published yet, or its category is '
                f'named unusually — pass the id explicitly in issues.py.')
        CAT = found['id']
        print(f'   category: {found["name"]} (id {CAT}, {found["count"]} posts)')

    API = ('https://palakneeti.in/wp-json/wp/v2/posts'
           f'?categories={CAT}&per_page=50&orderby=date&order=asc'
           '&_fields=id,date,slug,link,title,content,featured_media')

    return API

def fetch_image(url):
    """Download an image, normalising the name and converting formats that
       PowerPoint cannot embed."""
    # IMGDIR is None when this module is imported only for its parsers, so
    # nothing is downloaded and image blocks are simply skipped
    if not url or not IMGDIR:
        return None
    # the path may contain Devanagari, which must be percent-encoded
    parts = urllib.parse.urlsplit(url)
    safe = urllib.parse.urlunsplit((
        parts.scheme, parts.netloc,
        urllib.parse.quote(parts.path, safe='/%'), parts.query, ''))

    raw = os.path.basename(urllib.parse.unquote(parts.path))
    name = re.sub(r'[^A-Za-z0-9._-]', '_', raw) or 'img'
    path = os.path.join(IMGDIR, name)

    if not os.path.exists(path):
        try:
            req = urllib.request.Request(safe, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r, open(path, 'wb') as f:
                f.write(r.read())
        except Exception as e:
            print('  !! image failed:', url, e)
            return None

    # .webp cannot go into a .pptx — convert once, up front
    if name.lower().endswith('.webp'):
        png = os.path.splitext(path)[0] + '.png'
        if not os.path.exists(png):
            try:
                from PIL import Image
                Image.open(path).convert('RGBA').save(png)
            except Exception as e:
                print('  !! webp convert failed:', name, e)
                return None
        return os.path.basename(png)
    return name


# One March post crams two URLs into a single href separated by a comma, so
# the pattern stops at the comma and the first one wins.
DRIVE = re.compile(r'https?://(?:drive|docs)\.google\.com/[^\s"\'<>),]+')


def drive_pdf(html_src):
    """The hand-made edition PDF linked from a month index post."""
    m = DRIVE.search(html_src or '')
    return m.group(0) if m else None


def featured_urls(posts):
    """WordPress keeps the featured image outside the post content, so it has
       to be looked up separately — one request for the whole batch."""
    ids = sorted({p.get('featured_media') for p in posts if p.get('featured_media')})
    if not ids:
        return {}
    got = fetch_json('https://palakneeti.in/wp-json/wp/v2/media'
                     f'?include={",".join(str(i) for i in ids)}'
                     '&per_page=100&_fields=id,source_url,mime_type')
    # some posts use the issue's cover PDF as their featured media
    return {m['id']: m['source_url'] for m in got
            if (m.get('mime_type') or '').startswith('image/')}


def add_lead_image(blocks, url):
    """Put the featured image at the top of the article, unless the same
       picture already appears in the body."""
    if not url:
        return blocks
    here = {(b.get('src') or '').rsplit('/', 1)[-1]
            for b in blocks if b['type'] == 'image'}
    if url.rsplit('/', 1)[-1] in here:
        return blocks
    fn = fetch_image(url)
    if not fn:
        return blocks
    return [{'type': 'image', 'file': fn, 'src': url, 'caption': '',
             'lead': True, 'w': None, 'h': None}] + blocks


def main():
    api = setup(KEY_ARG)
    posts = fetch_json(api)
    media = featured_urls(posts)
    json.dump(posts, open(os.path.join(IDIR, 'raw.json'), 'w'), ensure_ascii=False)

    # The month index post is not an article — just links to the month's
    # pieces, and up to मे २०२६ the hand-made PDF. Keep the PDF, drop the post.
    kept, pdf_url = [], None
    for p in posts:
        title = re.sub(r'\s+', ' ',
                       BeautifulSoup(p['title']['rendered'], 'html.parser').get_text().strip())
        if is_month_index(title):
            pdf_url = pdf_url or drive_pdf(p['content']['rendered'])
            print(f'   index post skipped: {title}'
                  + (f'  (PDF: {pdf_url})' if pdf_url else '  (no PDF link)'))
            continue
        kept.append((p, title))

    out = []
    for p, title in kept:
        blocks = add_lead_image(to_blocks(p['content']['rendered']),
                                media.get(p.get('featured_media')))
        out.append(normalize(title, p['slug'], blocks, p))
    json.dump(out, open(os.path.join(IDIR, 'issue.json'), 'w'),
              ensure_ascii=False, indent=1)
    # read by mksite.py, so the front page can point at the hand-made PDF
    json.dump({'pdf_url': pdf_url},
              open(os.path.join(IDIR, 'issue-meta.json'), 'w'), ensure_ascii=False)

    print(f'{KEY}: {len(out)} articles')
    for a in out:
        imgs = [x['file'] for x in a['body'] if x['type'] == 'image']
        chars = sum(len(plain(x['runs'])) for x in a['body'] if x['type'] == 'para')
        print(f"  · {a['title'][:52]}")
        print(f"      byline={' / '.join(a['byline']) or '—'}  {chars} chars  imgs={imgs}")
        if a['tail']:
            print(f"      tail={a['tail']['name']} <{a['tail']['email']}> photo={a['tail']['photo']}")


if __name__ == '__main__':
    KEY_ARG = sys.argv[1] if len(sys.argv) > 1 else '2026-07'
    main()
