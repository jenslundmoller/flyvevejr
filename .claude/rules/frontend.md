---
description: Regler for siden i termik/output (cache, CSP, tekst)
paths:
  - "termik/output/**"
---

# Frontend

Siden er statisk HTML/CSS/JS på GitHub Pages med Leaflet fra unpkg. Ingen
build, ingen framework.

- **`CACHE_VERSION` i `sw.js` tælles op (`termik-vNN`) i samme push som
  enhver ændring af app-skallen** (`index.html`, `app.js`, `style.css`,
  `om.html`, ikoner, manifest). Service workeren serverer skallen
  cache-first; uden bump ser tilbagevendende besøgende den gamle version.
  `data/*.json` er network-first og kræver intet bump.
- **CSP sættes i `<meta>` i `index.html` og `om.html`** (GitHub Pages kan
  ikke sætte headers). Ingen inline `<script>`; ny ekstern kilde kræver at
  CSP'en udvides og at scriptet har SRI (`integrity` + `crossorigin`).
  Referrer-policy skal forblive `strict-origin-when-cross-origin`, ellers
  afviser OSM kortfliserne. Se `docs/Referat/2026-04-27-sikkerhed-csp-sri.md`.
- **Tekst fra JSON escapes** med `escapeHtml()` før den sættes i
  `innerHTML` (navn og kommentar er escapet; tal er ikke, åbent punkt 16).
- **Dansk UI-tekst, ingen tankestreg.** Højder mærkes med datum: "Termiktop
  QNH", "Skybase QFE".
- **Alle multi-level-felter kan mangle.** Layoutet må ikke vælte, når et
  felt er `null`.
- Tjek på mobil (<768 px, sidepanelet bliver bundpanel) og desktop.
  Lokalt: `cd termik/output && python3 -m http.server 8090`.
- Score-lagets farver (blå til rød) og termiktop-lagets (grå, lilla, orange,
  gul, grøn) må ikke ligne hinanden.
