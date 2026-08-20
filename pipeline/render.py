# -*- coding: utf-8 -*-
"""Drive the browser for pagination and printing.

    render.py dom <url>            page HTML, once the page says it is done
    render.py pdf <url> <outfile>  print to PDF, once the page says it is done

The page signals completion by setting document.title (Paged.js finishes
asynchronously, so there is no load event to wait on). Chrome's old
`--dump-dom --virtual-time-budget` pair used to approximate this, but newer
Chrome ignores the budget and dumps immediately — which produced a half
paginated page and a mystifying "never saw PAGEMAP". Waiting on the real
condition is both correct and faster, and needs no retry loop.
"""
import sys
from playwright.sync_api import sync_playwright

MARKERS = ('RENDER_DONE', 'EXTRACT_DONE')


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    mode, url = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else None
    want = 'EXTRACT_DONE' if url.endswith('#extract') else 'RENDER_DONE'

    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--allow-file-access-from-files'])
        page = browser.new_page()
        page.goto(url, wait_until='load', timeout=120_000)
        try:
            page.wait_for_function(
                'm => document.title === m', arg=want, timeout=300_000)
        except Exception:
            title = page.title()
            raise SystemExit(
                f'!! the page never reported {want} (title is {title!r}).\n'
                f'   Paged.js probably threw — open {url} in a browser to see.')

        if mode == 'dom':
            sys.stdout.write(page.content())
        elif mode == 'pdf':
            # honour @page size/margins from the stylesheet, and keep the
            # coloured panels, which Chrome drops from print by default
            page.pdf(path=out, prefer_css_page_size=True, print_background=True)
        else:
            raise SystemExit(f'unknown mode {mode!r}')
        browser.close()


main()
