# -*- coding: utf-8 -*-
"""Build author pages: one page per contributor listing everything they have
   written, each linking out to the original post on palakneeti.in.

       authors.py <repo-root> [year]

This is a navigation layer over the existing site — nothing on WordPress
changes. The articles are all posted by one WordPress account, so the real
author has to be read out of the article itself.
"""
import hashlib, html as H, json, os, re, sys, datetime
import fetchparse as fp
import chrome
from issues import is_month_index

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '..')
# accepts a year ("2026") or a month key ("2026-08"), so the workflow can
# pass whatever it already has
_arg = sys.argv[2] if len(sys.argv) > 2 else ''
YEAR = int(_arg.split('-')[0]) if _arg else datetime.date.today().year
FIRST_YEAR = 2025                          # how far back the index reaches
DOCS = os.path.join(ROOT, 'docs')
OUT = os.path.join(DOCS, 'authors')
esc = lambda t: H.escape(str(t), quote=False)

MASIK = 49          # the masik-article category
EDITORS = 'संपादक मंडळ'
MONTHS_MR = ['जानेवारी', 'फेब्रुवारी', 'मार्च', 'एप्रिल', 'मे', 'जून', 'जुलै',
             'ऑगस्ट', 'सप्टेंबर', 'ऑक्टोबर', 'नोव्हेंबर', 'डिसेंबर']
DEV = '०१२३४५६७८९'
dev = lambda n: ''.join(DEV[int(c)] if c.isdigit() else c for c in str(n))

ROLE_RE = re.compile(r'^(अनुवाद|शब्दांकन|छायाचित्र[े]?|संकलन)\s*[:：]\s*(.+)$')
SIGN_RE = re.compile(r'^(?:[–—-]\s*)?संपाद\w*\s*(?:मंडळ)?\s*,?\s*पालकनीती\s*$')


def clean(n):
    n = re.sub(r'\s+', ' ', (n or '')).strip(' .,:–—-')
    return re.sub(r'\s+\.', '.', n)          # "डॉ ." and "डॉ." are one person


def key_of(name):
    """Match names ignoring spacing, which varies between articles."""
    return re.sub(r'\s+', '', name or '').lower()


# Section labels sit in the same place as a byline. A person's name is at
# least two words and carries no sentence punctuation.
NOT_A_NAME = re.compile(r'[,?!।]|पूर्वार्ध|उत्तरार्ध|भाग\s')
LABELS = {'पुस्तक परिचय', 'संवादकीय', 'कविता', 'अर्थ', 'मनोगत',
          'अनुभव', 'संपादकीय', 'आदरांजली', 'निमित्त'}


def looks_like_person(name):
    n = clean(name)
    if not n or n in LABELS or NOT_A_NAME.search(n):
        return False
    return len(n.split()) >= 2


def slug_for(person):
    """A stable, URL-safe folder name. Emails give a readable one."""
    if person['email']:
        base = person['email'].split('@')[0].lower()
        base = re.sub(r'[^a-z0-9]+', '-', base).strip('-')
        if base:
            return base
    h = hashlib.md5(person['name'].encode('utf-8')).hexdigest()[:8]
    return 'p-' + h


def fetch_years(first, last):
    """Every masik article between two years, following pagination."""
    out, page = [], 1
    while True:
        batch = fp.fetch_json(
            'https://palakneeti.in/wp-json/wp/v2/posts'
            f'?categories={MASIK}&after={first - 1}-12-31T23:59:59'
            f'&before={last + 1}-01-01T00:00:00'
            f'&per_page=100&page={page}&orderby=date&order=desc'
            '&_fields=id,date,slug,link,title,content')
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def fetch_year(year):                      # kept for one-year callers
    return fetch_years(year, year)


AVATAR_PX = 96          # rendered at 40-48 css px, so 2x is plenty


def avatar(url, cache={}):
    """A small square JPEG data URI for the author's photo, or '' if the
       site does not actually have the file (older posts 404)."""
    if not url:
        return ''
    key = url
    if key in cache:
        return cache[key]
    out = ''
    try:
        import io, base64, urllib.request, urllib.parse
        from PIL import Image
        # Author photos are uploaded under their Marathi names, so the path
        # holds Devanagari and urlopen raises UnicodeEncodeError on it before
        # any request goes out — which the except below then swallowed as
        # "no photo". fetchparse.fetch_image has always quoted; this did not.
        _p = urllib.parse.urlsplit(url)
        url = urllib.parse.urlunsplit((_p.scheme, _p.netloc,
                                       urllib.parse.quote(_p.path, safe='/%'),
                                       _p.query, ''))
        req = urllib.request.Request(url, headers=fp.HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            im = Image.open(io.BytesIO(r.read()))
        im = im.convert('RGB')
        side = min(im.size)
        l, t = (im.width - side) // 2, (im.height - side) // 2
        im = im.crop((l, t, l + side, t + side)).resize(
            (AVATAR_PX, AVATAR_PX), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=78, optimize=True)
        out = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        out = ''
    cache[key] = out
    return out


def analyse(posts):
    """Pull the contributors out of each article.

    Two passes: the first takes the names that are unambiguous (an author card,
    or an explicit byline). The second uses those known names to rescue
    articles where the author's name was written as a heading, which otherwise
    reads as a section label like 'पुस्तक परिचय'.
    """
    parsed = []
    for p in posts:
        title = clean(H.unescape(re.sub('<[^>]+>', '', p['title']['rendered'])))
        if is_month_index(title):
            continue          # a list of links, not a piece of writing
        blocks = fp.to_blocks(p['content']['rendered'])
        a = fp.normalize(title, p['slug'], blocks, p)
        tail_txt = [fp.plain(b['runs']) for b in blocks[-6:]
                    if b['type'] in ('para', 'head')]
        parsed.append((p, title, a, blocks, tail_txt))

    known = {}                                   # name -> email (or None)
    for _, _, a, _, _ in parsed:
        if a['tail'] and a['tail']['name']:
            known.setdefault(key_of(clean(a['tail']['name'])), a['tail']['email'])
        for b in a['byline']:
            m = ROLE_RE.match(b)
            nm = clean(m.group(2) if m else b)
            if looks_like_person(nm):
                known.setdefault(key_of(nm), None)
    known.pop('', None)

    people, articles = {}, []

    def add(name, email, role, art, bio=None, photo=None):
        name = clean(name)
        if not name:
            return
        key = (email or '').lower() or key_of(name)
        # a name first seen without an email should merge into the email record
        k = key_of(name)
        if not email and known.get(k):
            key = known[k].lower()
            email = known[k]
        p = people.setdefault(key, {'name': name, 'email': email or '',
                                    'bio': '', 'photo': '', 'items': []})
        if photo and not p['photo']:
            p['photo'] = photo
        if email and not p['email']:
            p['email'] = email
        if bio and not p['bio']:
            p['bio'] = bio
        if len(name) > len(p['name']):
            p['name'] = name
        # the same person can be named twice for one article (an author card
        # plus an 'अनुवाद :' byline) — keep one entry and merge the roles
        for it in p['items']:
            if it['link'] == art['link']:
                roles = [r for r in (it['role'], role) if r]
                it['role'] = ' · '.join(dict.fromkeys(
                    r for r in roles if r != 'लेखन')) or 'लेखन'
                return
        p['items'].append(dict(art, role=role))

    for post, title, a, blocks, tail_txt in parsed:
        art = {'title': title, 'link': post['link'], 'date': post['date'][:10]}
        found = 0

        if a['tail'] and a['tail']['name']:
            add(a['tail']['name'], a['tail']['email'],
                a['tail'].get('role') or 'लेखन', art, a['tail'].get('bio'),
                a['tail'].get('photo_src'))
            found += 1

        for b in a['byline']:
            m = ROLE_RE.match(b)
            nm = clean(m.group(2) if m else b)
            role = m.group(1) if m else 'लेखन'
            if a['tail'] and key_of(clean(a['tail']['name'])) == key_of(nm) and not m:
                continue                          # already added from the card
            if not m and not looks_like_person(nm):
                continue                          # a section label, not a person
            add(nm, None, role, art)
            found += 1

        if not found:
            # the name may have been written as a heading — accept it only if
            # we have seen that person elsewhere, so section labels are not
            # mistaken for people
            # the name may sit in a heading of any level, which the layout
            # parser treats as a section label rather than a byline
            texts = [b for b in blocks if b['type'] in ('head', 'para')][:3]
            heads = [clean(a['kicker'])] + [
                clean(fp.plain(b.get('runs', []))) for b in texts]
            for k in heads:
                if k and key_of(k) in known:
                    add(k, known[key_of(k)], 'लेखन', art)
                    found += 1
                    break
            for t in tail_txt:                    # a trailing 'अनुवाद : X'
                m = ROLE_RE.match(clean(t))
                if m:
                    add(m.group(2), None, m.group(1), art)
                    found += 1
            if not found:
                for t in tail_txt:                # '– संपादक, पालकनीती'
                    if SIGN_RE.match(clean(t)) or 'संपादक मंडळ' in t:  # editorial piece
                        add(EDITORS, None, 'संपादकीय', art)
                        found += 1
                        break
        articles.append((art, found))

    for p in people.values():
        p['items'].sort(key=lambda x: x['date'], reverse=True)
        p['slug'] = slug_for(p)
    return people, articles


PAGE_CSS = """
/* the palette, bar and controls come from chrome.py */
.crumb{font-size:.86rem;color:var(--faint);margin:1.6rem 0 1.2rem}
.crumb a{color:var(--soft);text-decoration:none}
.crumb a:hover{color:var(--moss)}
h1{font-family:var(--serif);font-weight:400;font-size:clamp(1.9rem,8vw,2.5rem);
 margin:0 0 .2rem;color:var(--moss);line-height:1.15}
.tag{color:var(--faint);margin:0 0 1.8rem;font-size:.9rem}
.hero{display:flex;gap:1rem;align-items:center;margin:0 0 1.4rem}
.hero .av{width:74px;height:74px;border-radius:50%;object-fit:cover;flex:none;
 background:var(--surface)}
.hero .av.none{display:grid;place-items:center;font-family:var(--serif);
 color:var(--faint);font-size:1.8rem}
.hero h1{margin:0}
.hero .tag{margin:.2rem 0 0}
.bio{background:var(--surface);border-radius:5px;padding:1rem 1.15rem;
 margin:0 0 1.8rem;font-size:.95rem;color:var(--soft)}
.bio a{color:var(--moss);word-break:break-all}
.who{border-top:1px solid var(--rule);padding:.85rem 0;display:flex;
 align-items:center;gap:.8rem}
.who .av{width:42px;height:42px;border-radius:50%;object-fit:cover;flex:none;
 background:var(--surface)}
.who .av.none{display:grid;place-items:center;font-family:var(--serif);
 color:var(--faint);font-size:1.05rem}
.who .nm{flex:1;min-width:0}
.who:last-of-type{border-bottom:1px solid var(--rule)}
.who a{font-family:var(--serif);font-size:1.18rem;color:var(--ink);
 text-decoration:none;line-height:1.3;display:block}
.who .n{color:var(--faint);font-size:.86rem;white-space:nowrap;
 font-variant-numeric:tabular-nums}
@media (hover:hover){.who a:hover{color:var(--moss)}}
.yr{font-family:var(--sans);font-size:.78rem;letter-spacing:.16em;
 text-transform:uppercase;color:var(--faint);margin:1.8rem 0 .2rem}
ol.arts{list-style:none;margin:0;padding:0}
ol.arts li{border-top:1px solid var(--rule);padding:1rem 0}
ol.arts li:last-child{border-bottom:1px solid var(--rule)}
ol.arts a{font-family:var(--serif);font-size:1.18rem;color:var(--ink);
 text-decoration:none;line-height:1.35;display:block}
@media (hover:hover){ol.arts a:hover{color:var(--moss)}}
.meta{margin-top:.3rem;font-size:.85rem;color:var(--faint)}
.meta .role{color:var(--clay)}
.out{font-size:.78rem;color:var(--faint);margin-left:.35rem}
footer{margin-top:2.6rem;padding-top:1.4rem;border-top:1px solid var(--rule);
 color:var(--faint);font-size:.87rem}
footer a{color:var(--moss)}
"""


def shell(title, body, home, label):
    inner = (f'<main><p class="crumb"><a href="{home}">← पालकनीती मासिक</a></p>'
             f'{body}'
             f'<footer><p>लेख <a href="https://palakneeti.in" target="_blank"'
             f' rel="noopener">palakneeti.in</a> वर उघडतील. ही यादी त्या'
             f' संकेतस्थळावरून आपोआप तयार होते.</p>'
             f'<p><a class="backlink" href="{home}">← सगळे अंक</a></p></footer></main>')
    return chrome.page(title, PAGE_CSS, inner, home=home, label=label,
                       progress=False)


def article_list(items):
    """Grouped by year, newest first."""
    out, year = [], None
    for it in items:
        y, m, _ = it['date'].split('-')
        if y != year:
            if year is not None:
                out.append('</ol>')
            out.append(f'<p class="yr">{dev(y)}</p><ol class="arts">')
            year = y
        role = (f'<span class="role">{esc(it["role"])}</span> · '
                if it['role'] and it['role'] != 'लेखन' else '')
        out.append(f'<li><a href="{esc(it["link"])}" target="_blank"'
                   f' rel="noopener">{esc(it["title"])}<span class="out">↗</span></a>'
                   f'<div class="meta">{role}{MONTHS_MR[int(m) - 1]}</div></li>')
    out.append('</ol>')
    return '\n'.join(out)


def av_html(p, cls='av'):
    if p.get('img'):
        return f'<img class="{cls}" src="{p["img"]}" alt="" loading="lazy">'
    return f'<span class="{cls} none">{esc(p["name"][:1])}</span>'


def build():
    posts = fetch_years(FIRST_YEAR, YEAR)
    people, articles = analyse(posts)
    os.makedirs(OUT, exist_ok=True)
    span = (f'{dev(FIRST_YEAR)}–{dev(YEAR)}' if YEAR > FIRST_YEAR else dev(YEAR))

    for p in people.values():
        p['img'] = avatar(p.get('photo'))
    ranked = sorted(people.values(), key=lambda p: (-len(p['items']), p['name']))
    print(f'  {sum(1 for p in ranked if p["img"])}/{len(ranked)} have a usable photo')

    for p in ranked:
        d = os.path.join(OUT, p['slug'])
        os.makedirs(d, exist_ok=True)
        bio = ''
        if p['bio'] or p['email']:
            mail = (f'<p style="margin:.5rem 0 0"><a href="mailto:{esc(p["email"])}">'
                    f'{esc(p["email"])}</a></p>' if p['email'] else '')
            bio = f'<div class="bio">{esc(p["bio"])}{mail}</div>'
        body = (f'<div class="hero">{av_html(p)}<div>'
                f'<h1>{esc(p["name"])}</h1>'
                f'<p class="tag">{dev(len(p["items"]))} लेख · {span}</p>'
                f'</div></div>{bio}{article_list(p["items"])}')
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(
            shell(f'{p["name"]} — पालकनीती', body, '../../', p['name']))

    rows = ''.join(
        f'<div class="who">{av_html(p)}<span class="nm">'
        f'<a href="{p["slug"]}/">{esc(p["name"])}</a></span>'
        f'<span class="n">{dev(len(p["items"]))} लेख</span></div>'
        for p in ranked)
    attributed = sum(1 for _, f in articles if f)
    # articles, not posts: the month index posts are not writing
    body = (f'<h1>लेखक</h1><p class="tag">{span} · {dev(len(ranked))} लेखक · '
            f'{dev(len(articles))} लेख</p>{rows}')
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(
        shell('लेखक — पालकनीती', body, '../', 'लेखक'))

    # web.py reads this to show the same face and count beside every byline
    json.dump({p['name']: {'slug': p['slug'], 'n': len(p['items']),
                           'img': p['img'], 'span': span} for p in ranked},
              open(os.path.join(OUT, 'map.json'), 'w'), ensure_ascii=False)

    print(f'  {len(articles)} articles {span} ({len(posts)} posts, '
          f'{len(posts) - len(articles)} month index); {attributed} attributed, '
          f'{len(articles) - attributed} without a named author')
    print(f'  {len(ranked)} contributors')
    for p in ranked[:8]:
        print(f'    {len(p["items"]):3}  {p["name"]}  → authors/{p["slug"]}/')


if __name__ == '__main__':
    build()
