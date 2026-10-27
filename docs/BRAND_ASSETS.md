# Marketplace brand assets

Retrieved on 27 October 2026 for marketplace identification in the AnalyMark
university MVP. Files are stored in `static/images/marketplaces/` and served by
Django static files, without runtime requests to the publishers. The original
downloaded bytes, aspect ratios and colors are preserved. All five logos share
bounded containers with `object-fit: contain`: 112 × 40 px on coverage cards,
104 × 36 px in content, and 96 × 36 px in the sidebar. Light content uses transparent
containers; the dark sidebar uses the same pale neutral contrast surface for all
five brands. No logo-specific white rectangles or competing brand-colored badges
are added. Wide wordmarks naturally occupy less vertical space than square icons.

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
project-specific permission was verified for any of these five files, and no
specific attribution grant is claimed. The links and publisher credits above
record their origins, not a license. Ozon's listing identifies copyright as
Internet Solutions LLC (Ozon group). Other brands remain their owners' property.

The logos identify marketplace labels only: AnalyMark has no claimed partnership,
endorsement or live competitor feed. Confirm applicable trademark/asset permission
with the owners before commercial use; do not assume the repository's own code
terms grant rights to these assets. Do not use an authorized-partner badge.

## Integrity (SHA-256)

```text
89e3615a7f47b46eb66bd3bd70be9110f97e2189d4eaea6f3887e79b4874e789  kaspi.svg
1cb7904443cd7313d2213de70f58d26b38bc6f4d6ee8def835b31c6f0d5eec73  halyk.svg
6dd2ca9038f08c90e6ef3a9722f88fbe40129c0b556fc3f65b30374eaa6a071f  wildberries.svg
09aa5a0ef03660c222491275bbbb8d02de07e43401e7b7a2f3fd1b68daf56abc  ozon.webp
0d11aa4b85d8eb0c1eb1f2ada8e0c821425835260fe1380537fadf4c6ff10652  teez.webp
```

The SVGs were checked for scripts, embedded images, event handlers and external
references. No generated initials/symbols are used for the five active brands.
Archived/unrecognized marketplaces retain a neutral archive symbol.
