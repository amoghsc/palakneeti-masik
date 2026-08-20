# -*- coding: utf-8 -*-
"""Per-issue configuration and the two visual styles."""

ISSUES = {
    '2026-07': {
        'category': 765,
        'month_mr': 'जुलै २०२६', 'month_en': 'July 2026',
        'varsha': '२६', 'ank': '४',
        'style': 'classic',
        'cover': {'mode': 'blank'},
        'out': 'palakneeti_2026_07',
    },
    '2026-07-v2': {
        'category': 765,
        'data': '2026-07',          # reuse the articles already fetched for July
        'month_mr': 'जुलै २०२६', 'month_en': 'July 2026',
        'varsha': '२६', 'ank': '४',
        'style': 'twocol',
        'fit_threshold': 0.62,
        'cover': {'mode': 'text', 'title': 'Palakniti', 'subtitle': 'July 2026'},
        'out': 'palakneeti_2026_07_v2_twocolumn',
    },
    '2026-08': {
        'category': 769,
        'month_mr': 'ऑगस्ट २०२६', 'month_en': 'August 2026',
        'varsha': '२६', 'ank': '५',
        'style': 'editorial',
        'cover': {'mode': 'text', 'title': 'Palakniti', 'subtitle': 'August 2026'},
        'out': 'palakneeti_2026_08',
    },
}

SITE = 'www.palakneeti.in'

# ── palettes ────────────────────────────────────────────────────────────
PALETTES = {
    'twocol': {           # same colours as July v1, so only the layout differs
        'teal':   '#12615B',
        'teal_d': '#0B4A45',
        'orange': '#E8823C',
        'peach':  '#FBE1CC',
        'mint':   '#DEEFEC',
        'ink':    '#1A1A1A',
        'grey':   '#5C6663',
    },
    'classic': {          # as printed in the May 2026 issue
        'teal':   '#12615B',
        'teal_d': '#0B4A45',
        'orange': '#E8823C',
        'peach':  '#FBE1CC',
        'mint':   '#DEEFEC',
        'ink':    '#1A1A1A',
        'grey':   '#5C6663',
    },
    'editorial': {        # same family, warmer and deeper
        'teal':   '#2F5D50',
        'teal_d': '#1E4238',
        'orange': '#C9622F',
        'peach':  '#F4E7D9',
        'mint':   '#E6EFE9',
        'ink':    '#1F1F1D',
        'grey':   '#5E6763',
    },
}

# the standing masthead, carried over from the printed issues
MASTHEAD = [
    ('संपादक :', ['संजीवनी कुलकर्णी']),
    ('कार्यकारी संपादक :', ['अनघा जलतारे']),
    ('संपादक मंडळ :', ['प्रीती पुष्पा-प्रकाश, रुबी रमा प्रवीण,',
                       'प्रणाली सिसोदिया, कृणाल देसाई,',
                       'प्रीतम मनवे, ज्योती दळवी, अमृता ढगे,',
                       'अमोघ चौगुले, विक्रांत पाटील,',
                       'ऋषिकेश भरड, स्मिता वळसंगकर']),
    ('विश्वस्त :', ['संजीवनी कुलकर्णी, नीलिमा सहस्रबुद्धे, शुभदा जोशी,',
                    'वंदना कुलकर्णी, प्रियंवदा बारभाई,',
                    'डॉ. विनय कुलकर्णी, रमाकांत धनोकर']),
    ('मुखपृष्ठ, अंक सजावट आणि मांडणी :', ['अमृता ढगे']),
    ('आतील चित्रे :', ['इंटरनेटवरून साभार']),
]


# ── resolving a month without editing this file ──────────────────────────
# A new issue should need nothing but its key, e.g. "2026-09". The month
# names are derived, and the WordPress category is looked up by name.
MONTHS = [('January', 'जानेवारी'), ('February', 'फेब्रुवारी'), ('March', 'मार्च'),
          ('April', 'एप्रिल'), ('May', 'मे'), ('June', 'जून'), ('July', 'जुलै'),
          ('August', 'ऑगस्ट'), ('September', 'सप्टेंबर'), ('October', 'ऑक्टोबर'),
          ('November', 'नोव्हेंबर'), ('December', 'डिसेंबर')]

_DEV = '०१२३४५६७८९'
_dev = lambda s: ''.join(_DEV[int(c)] if c.isdigit() else c for c in str(s))

DEFAULTS = {'style': 'classic', 'cover': {'mode': 'blank'},
            'varsha': '', 'ank': ''}


def month_parts(key):
    """'2026-09' or '2026-09-v2' -> (2026, 9)."""
    bits = key.split('-')
    return int(bits[0]), int(bits[1])


def resolve(key):
    cfg = dict(DEFAULTS)
    cfg.update(ISSUES.get(key, {}))
    # a build form (or a shell) can override without editing this file
    import os as _os
    if _os.environ.get('PN_STYLE'):
        cfg['style'] = _os.environ['PN_STYLE']
    if _os.environ.get('PN_COVER') == 'title':
        cfg['cover'] = {'mode': 'text', 'title': 'Palakniti',
                        'subtitle': None}      # filled in below
    elif _os.environ.get('PN_COVER') == 'blank':
        cfg['cover'] = {'mode': 'blank'}
    if 'month_mr' not in cfg:
        y, m = month_parts(key)
        en, mr = MONTHS[m - 1]
        cfg['month_mr'] = f'{mr} {_dev(y)}'
        cfg['month_en'] = f'{en} {y}'
    if cfg.get('cover', {}).get('subtitle') is None and cfg['cover'].get('mode') == 'text':
        cfg['cover'] = dict(cfg['cover'], subtitle=cfg['month_en'])
    cfg.setdefault('out', 'palakneeti_' + key.replace('-', '_'))
    return cfg


def find_category(key, fetch_json):
    """Locate the WordPress category for a month by name.

    Category names are written inconsistently on the site — 'जुलै २०२६ - July
    2026', 'June 2026 - जून २०२६' — so match on the English month name plus the
    year in either script, and require the category to actually hold posts.
    """
    y, m = month_parts(key)
    en, mr = MONTHS[m - 1]
    years = {str(y), _dev(y)}
    hits, page = [], 1
    while page <= 6:
        try:
            cats = fetch_json('https://palakneeti.in/wp-json/wp/v2/categories'
                              f'?per_page=100&page={page}'
                              '&_fields=id,name,slug,count')
        except Exception:
            break
        if not cats:
            break
        for c in cats:
            hay = (c['name'] + ' ' + urllib_unquote(c['slug'])).lower()
            if c['count'] < 1:
                continue
            if not any(yr in hay for yr in years):
                continue
            if en.lower() in hay or mr in hay:
                hits.append(c)
        page += 1
    # prefer the most specific name (a single month beats 'Aug-Sep')
    hits.sort(key=lambda c: len(c['name']))
    return hits[0] if hits else None


def urllib_unquote(s):
    import urllib.parse
    return urllib.parse.unquote(s)
