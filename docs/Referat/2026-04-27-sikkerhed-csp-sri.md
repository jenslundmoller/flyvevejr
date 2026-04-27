# Sikkerhedshærdning: CSP, SRI og referrer-policy

**Dato:** 2026-04-27
**Commit:** `e66c816 security: tilføj CSP, SRI på unpkg-CDN og strict referrer-policy`

## Udgangspunkt

Spørgsmål fra bruger: er der noget sikkerhedsmæssigt at være opmærksom på, når siden ikke har direkte brugerinput? Sitet er en statisk PWA hostet på GitHub Pages — ren read-only forecast-visning baseret på `current.json` + `denmark.geojson`. Ingen formularer, ingen API-keys i frontend, ingen tredjeparts-tracking. Angrebsfladen er lille, men ikke nul.

## Fundne risici (prioriteret)

1. **CDN uden integrity-hash.** `index.html` hentede Leaflet 1.9.4 CSS+JS fra `unpkg.com` uden `integrity`. Hvis unpkg eller pakken kompromitteres, eksekverer Leaflet vilkårlig JS i klienten. Værre: service workeren cacher `unpkg`-URL'erne **cache-first**, så en kompromitteret fil ville blive låst i klienten indtil næste `CACHE_VERSION`-bump.
2. **`innerHTML` med JSON-felter.** `createPopupContent` bygger HTML via streng-konkatenering. `airfield.name` og `hourData.comment` køres gennem `escapeHtml()`, men numeriske felter (`d.temp`, `d.wind_dir` osv.) interpoleres direkte. Lavrisiko nu (egen pipeline genererer JSON), men forward-fragile hvis nye felter får eksterne kilder.
3. **Manglende sikkerhedsheaders.** GitHub Pages sætter ikke CSP, Referrer-Policy m.m. CSP ville begrænse skader hvis enten CDN eller en innerHTML-bug blev udnyttet.
4. **HTTPS ikke håndhævet.** Custom domain via `CNAME` — uden "Enforce HTTPS" kan brugere ramme HTTP og blive MITM-injiceret.

## Implementerede mitigationer

### SRI på unpkg
Begge unpkg-tags fik `integrity="sha256-..."` + `crossorigin="anonymous"`. Browseren afviser nu filerne hvis indholdet er ændret, selv hvis cache eller CDN er kompromitteret.

### Content Security Policy via `<meta http-equiv>`
GitHub Pages tillader ikke custom HTTP-headers, så CSP er sat via meta-tag. Direktiver:
- `default-src 'self'`
- `script-src 'self' https://unpkg.com` (intet `'unsafe-inline'` — krævede at flytte SW-registreringen fra inline `<script>` i `index.html` til bunden af `app.js`)
- `style-src 'self' https://unpkg.com 'unsafe-inline'` (`'unsafe-inline'` nødvendig pga. mange `style="..."`-attributter i popups)
- `img-src 'self' data: blob: https://*.tile.openstreetmap.org` (data: for SVG-favicon, tile-host for Leaflet)
- `connect-src 'self' https://unpkg.com` (unpkg kun for sourcemaps i DevTools)
- `manifest-src 'self'`, `worker-src 'self'`
- `object-src 'none'`, `base-uri 'self'`
- `frame-ancestors` udeladt — virker ikke via meta og kræver HTTP-header (kan sættes hvis vi senere flytter til Cloudflare/Netlify)

### Referrer-policy
Først forsøgt `no-referrer`. Det brød OSM tile-loading: OSM's gratis volunteer-servere returnerer 403 hvis Referer-headeren mangler. Ændret til `strict-origin-when-cross-origin` (moderne browser-default) — sender kun `https://dit-domæne/` til tredjeparter, ikke fulde URL.

### Service worker bumps
Cache-version bumpet til `termik-v12` så klienter henter nyt app shell med SRI + CSP i stedet for at fortsætte på gammelt cachet shell.

## Forløb i iterationer

### Iteration 1: Initial CSP (for stram)
Første CSP-version brød siden:
- `frame-ancestors 'none'` → browser-warning (ignoreres i meta).
- OSM tiles blokeret af `img-src 'self' data: blob:` (ingen tile-host whitelisted).
- Unpkg sourcemap blokeret af `connect-src 'self'`.

### Iteration 2: Tilladte hosts tilføjet
`*.tile.openstreetmap.org` til `img-src`, `unpkg.com` til `connect-src`, `frame-ancestors` fjernet. Tiles kom delvist tilbage — men erstattet af "Access blocked / Referer is required" 403-tiles fra OSM.

### Iteration 3: Referrer-policy lempet
`no-referrer` → `strict-origin-when-cross-origin`. Tiles loadede normalt. Console ren.

## Brugersiden (manuel handling)

- **Enforce HTTPS** aktiveret af bruger i GitHub Pages settings → Pages → Custom domain.

## Ændrede filer

- `termik/output/index.html` — SRI på Leaflet CSS+JS, CSP meta-tag, referrer-meta, fjernet inline SW-registrering.
- `termik/output/app.js` — SW-registrering flyttet hertil.
- `termik/output/sw.js` — `CACHE_VERSION` v9 → v12.

## Forkastede / overvejede

- **Fuld `escapeHtml()` på alle popup-felter.** Defensiv forbedring, men lavrisiko nu hvor JSON kommer fra egen pipeline. Gemt som fremtidigt skridt.
- **Self-host Leaflet i `vendor/`** for at fjerne CDN-afhængighed helt. Ville lade os droppe `unpkg.com` fra `script-src`/`style-src`/`connect-src` og stramme CSP'en. Ikke gjort denne gang.
- **`X-Frame-Options: DENY` / `frame-ancestors`-header.** Kræver flytning fra GitHub Pages til hosting der tillader custom headers.

## Mulige næste skridt

- Self-host Leaflet (lille, ~150 KB) → skarpere CSP.
- Defensiv escape af alle JSON-felter i `createPopupContent`.
- Hvis vi flytter til Cloudflare/Netlify: tilføj `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security` som ægte HTTP-headers.
