# Cover images

Put a month's cover here and the next build will use it, full page, no
margins.

## How

1. **Add file → Upload files** (the button at the top of this folder on
   GitHub). That page has a real file picker — the *Run workflow* form does
   not, which is why covers live here.
2. Name the file for the month: **`2026-09.jpg`**. `.jpeg`, `.png` and
   `.webp` work too.
3. **Commit changes.**
4. Run **Build issue** for that month as usual.

That is all. There is no extra box to tick — having the file here is the
instruction.

## Size

The page is A4, and the image is scaled to fill it and centred, so anything
that does not share A4's proportions loses its edges. To keep control of
what is cropped, supply the image at A4 proportions:

| | pixels |
|---|---|
| good | 1654 × 2339 (200 dpi) |
| best for print | 2480 × 3508 (300 dpi) |

## Going back to the standard cover

Delete the file, or run the build with **Cover page = `blank`**, which wins
over anything here and leaves an empty page for hand artwork.
