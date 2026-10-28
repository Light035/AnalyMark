# Marketplace brand assets

Retrieved on 27–28 October 2026 for marketplace identification in the AnalyMark
university MVP. Files are stored in `static/images/marketplaces/` and served by
Django static files, without runtime requests to the publishers. The original
downloaded bytes, aspect ratios and colors are preserved. All five logos share
bounded containers with `object-fit: contain`: 40 × 40 px on coverage cards and
36 × 36 px in content and sidebar icons. All active contexts use one shared image
partial, so the sidebar, coverage cards, offers, analytics, history and Watchlist
display the same assets. Light content uses transparent containers; no extra white
backing or neutral placeholder symbols are added. Earlier wordmarks, the black
Wildberries company-site icon and seasonal downloads are retained unchanged but
are not used by active marketplace identity templates.
Every sidebar row has one normal text label, which supplies the
accessible link name; decorative images use empty alt text and are hidden from
assistive technology to avoid repeating the name. The same five shortcuts remain
available in a compact row below the primary navigation on small screens.

The Kaspi SVG has a 141 × 33 viewBox, Halyk 720 × 85.04, and Wildberries 30 × 30.
These SVG backgrounds are transparent. Ozon and Teez are original 400 × 400 WebP
app icons with alpha transparency; their colored artwork is part of the asset.

## Provenance

| File | Official source / publisher | Original asset |
| --- | --- | --- |
| `kaspi.svg` | [Kaspi.kz](https://kaspi.kz/ru) | [Website wordmark](https://kaspi.kz/img/Logo.svg) |
| `halyk.svg` | [Halyk Market](https://halykmarket.kz/) | [Website wordmark](https://halykmarket.kz/_nuxt/7bd754a785536548302e95434aa08ccd.svg) |
| `wildberries.svg` | [RWB, owner of Wildberries](https://rwb.ru/) | [Wildberries icon used on its company website](https://rwb.ru/assets/svg/wb-logo.svg) |
| `ozon.webp` | [Ozon app, publisher OZON.ru / INTERNET SOLUTIONS, LLC](https://apps.apple.com/ru/app/id407804998) | [400px publisher app icon](https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/04/73/b9/0473b968-8fd1-29b1-16c1-4944253e813e/Placeholder.mill/400x400Icon.ApSiOS01-75.webp) |
| `teez.webp` | [Teez app, publisher Teez / Teez Technologies, Too](https://apps.apple.com/kz/app/id6618139935) | [400px publisher app icon](https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/0a/45/2f/0a452f48-530c-1103-3a1a-3b26a3f65eb7/Placeholder.mill/400x400Icon.ApSiOS01-75.webp) |

The `Placeholder.mill` path is Apple's asset naming, not an AnalyMark-generated
placeholder. Both downloaded icons were visually inspected. App artwork can
change seasonally; these are the publisher versions retrieved on the date above.
The Wildberries SVG is the official black icon, not a recolored purple logo.

Ozon's [official brand resource](https://brandlab.ozon.ru/) and
[logo rules](https://brandlab.ozon.ru/guide/logo_guide) were inspected. The downloaded
logo SVG contains a multi-variant brand sheet, while the separate icon archive
contains AI/EPS/PDF files. Rather than crop or redraw those assets, this MVP uses
the publisher's app icon. Teez's website image download was unavailable, so its
official publisher app artwork is used instead. No access controls or certificate
validation were bypassed.

## Rights and attribution

These are third-party trademarks/artworks, not AnalyMark creations. Official
publication verifies provenance; it does **not** establish an open-source license
or permission for unrestricted redistribution. No explicit open license or
project-specific permission was verified for any of these assets, and no
specific attribution grant is claimed. The links and publisher credits above
record their origins, not a license. Ozon's listing identifies copyright as
Internet Solutions LLC (Ozon group). Other brands remain their owners' property.

The logos identify marketplace labels only: AnalyMark has no claimed partnership,
endorsement or live competitor feed. Confirm applicable trademark/asset permission
with the owners before commercial use; do not assume the repository's own code
terms grant rights to these assets. Do not use an authorized-partner badge.

## Ordinary Kaspi and Wildberries icons, verified 28 October 2026

Google Play currently serves the ordinary red Kaspi symbol without “Жұма” and
the ordinary purple/pink WB symbol without “11.11”. These original 240 × 240 PNGs
are used throughout the application. They were downloaded from the icon links in
the official publisher listings, visually inspected and copied byte-for-byte.

| File | Publisher listing | Original image |
| --- | --- | --- |
| `kaspi-icon.png` | [Kaspi.kz on Google Play](https://play.google.com/store/apps/details?id=kz.kaspi.mobile) | [Original icon](https://play-lh.googleusercontent.com/XPRGdoE4SU2uK_L-vdR6Ab6_X4-6Vr4TFLDniHjX1tWlVe795uxV1MiJRFXZ0aTv9wMIiCHUKi4lnNOX74mwhxk=w240-h480) |
| `wildberries-icon.png` | [Wildberries LLC on Google Play](https://play.google.com/store/apps/details?id=com.wildberries.ru) | [Original icon](https://play-lh.googleusercontent.com/_3OFXp7p3aaOt6lJdqOPNS8frRjGW7SrlgUELTcxMZNbvQtBN0ez_lrXtMk-X9Yk_kfdesM7fOcRpMl3Ebhgpg=w240-h480) |

The App Store listings below were rechecked on the same date and still served
seasonal Kaspi/Wildberries artwork. Those seasonal files are retained for
provenance, not displayed. No campaign text was erased or cropped out. This is
a dated store comparison, not a claim that every store always has the same art.

## App Store artwork, retrieved 28 October 2026

The following original 400 × 400 WebP assets were downloaded from the `400w`
image sources in the publisher's
App Store listings, visually inspected, and retained byte-for-byte, including alpha
transparency and any seasonal lettering. No cropping, recoloring or redrawing is
used. The retained Kaspi file includes “Жұма” and Wildberries includes “11.11”;
those are publisher campaigns, not AnalyMark text. Only `halyk-app.webp` from this
table is used in the active UI. Ozon and Teez use the existing app assets.

| File | Publisher listing | Original image |
| --- | --- | --- |
| `kaspi-app.webp` | [Kaspi.kz, Kaspi Bank AO](https://apps.apple.com/kz/app/id1195076505) | [400px app icon](https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/f1/04/26/f10426a6-2a3e-7b74-30a9-1a9268620fd0/Placeholder.mill/400x400Icon.ApSiOS01-75.webp) |
| `halyk-app.webp` | [Halyk Kazakhstan, JSC Halyk Bank of Kazakhstan](https://apps.apple.com/kz/app/halyk-kazakhstan/id440635615) | [400px app icon](https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/58/65/5a/58655a71-bca2-156c-7ac8-5fcaa7195bc4/Placeholder.mill/400x400Icon.ApSiOS01-75.webp) |
| `wildberries-app.webp` | [WILDBERRIES, Wildberries OOO](https://apps.apple.com/us/app/wildberries/id597880187) | [400px app icon](https://is1-ssl.mzstatic.com/image/thumb/PurpleSource221/v4/e8/fa/ee/e8faee62-1857-db9d-a6cd-5908fffdbe6a/Placeholder.mill/400x400Icon.ApSiOS01-75.webp) |

Halyk's asset identifies the Halyk superapp, not a claimed standalone Market app.
The bank's [official Market instructions](https://hlb.halykbank.kz/market) direct
buyers to open Halyk Market within that app. Publisher provenance does not grant
an open license; the rights limitations above apply to these assets as well.

## Integrity (SHA-256)

```text
89e3615a7f47b46eb66bd3bd70be9110f97e2189d4eaea6f3887e79b4874e789  kaspi.svg
1cb7904443cd7313d2213de70f58d26b38bc6f4d6ee8def835b31c6f0d5eec73  halyk.svg
6dd2ca9038f08c90e6ef3a9722f88fbe40129c0b556fc3f65b30374eaa6a071f  wildberries.svg
09aa5a0ef03660c222491275bbbb8d02de07e43401e7b7a2f3fd1b68daf56abc  ozon.webp
0d11aa4b85d8eb0c1eb1f2ada8e0c821425835260fe1380537fadf4c6ff10652  teez.webp
fc0f98cc9b5815bd66fcecd2ca9d02291aa880b4ea808b44390e2052a78f6b49  kaspi-app.webp
ab97cb3a2995c13c8c1b8d16aed223f1f8f6e61e78628c3ae92a275c074c6b5c  halyk-app.webp
fd1396e36358c0a395508a6642254d059233cf7e47fa02618f82dd31c51b3399  wildberries-app.webp
05e80a14b4f3b23724de4d34cacd1615b8a05a988ecf471d121c8ebceaf990aa  kaspi-icon.png
bb2faa1c431b9c06139a69ee32001ba2bf70e3258821e4ea0ee530639d7a4c87  wildberries-icon.png
```

The SVGs were checked for scripts, embedded images, event handlers and external
references. No generated initials/symbols are used for the five active brands.
Archived/unrecognized marketplaces retain a neutral archive symbol.
