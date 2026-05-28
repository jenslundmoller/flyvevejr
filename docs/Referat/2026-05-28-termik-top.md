# Referat 2026-05-28: Termik-tophøjde + Indstillinger-panel

## Beslutninger

- **Metode B valgt**: TI=0 højde via tør-adiabatisk parcel-løft på Open-Meteo multilevel-sondering, cap'd med LCL og Hcrit-korrigeret.
- **Ingen MetPy** — egen ~120 linjers Python-implementation. Sparer ~200 MB dependencies; KISS når geopotential_height er givet direkte.
- **Bolton 1980 eq. 22** for LCL-temperatur (~10 m nøjagtighed). Den eksisterende `skybase_m = spread × 125`-formel bevares til scoring/comments, parcel-LCL bruges kun til termik-top.
- **Hcrit-margin lineær** 200 m (SW≥600 W/m²) til 500 m (SW≤0), cap'd til raw_top/2 så margin ikke æder hele beregningen. Glat overgang → ingen trin-spring mellem nabotimer.
- **Trykniveauer**: 950/925/900/850/800/700/600 hPa. 500 hPa droppet (DK termik når sjældent dertil).
- **`limited_by`-tilstande**: `lcl`, `ti_zero`, `cap`, `inversion`, `weak_solar`, `saturated`, `no_data`, `no_dewpoint`, `margin_collapse`. None-returns ved manglende data så frontend skiller "ukendt" fra "rigtig 0".
- **Nyt kortlag** med diskrete celler (canvas, smoothing=false), distinkt viridis-palet lilla→orange for at undgå forveksling med score's blå→rød. Numeriske labels per celle ved zoom ≥ 9.
- **Indstillinger-panel** i sidebar med radioknapper (kun ét lag aktivt). Valg huskes i localStorage.

## Proces

5-trins workflow med parallel agent-review:
1. To research-agenter (meteorologi + frontend)
2. Plan v1
3. To plan-review-agenter (kode + meteorologi) → fandt 5 P0 + flere P1/P2
4. Plan v2 + implementering
5. To kode-review-agenter (kommende)

## Vigtige bugfix under implementering

`d_prev <= 0` ved `i==1` triggrer falsk inversion fordi parcel ved surface = environment ved surface (d_prev = 0 by definition). Rettet til at tjekke parcel-vs-env ved `env[1]` (første niveau over jorden), så `d_prev >= 0` ved krydsning.

## Filer ændret

| Fil | Ændring |
|-----|---------|
| `termik/scoring.py` | +`compute_thermal_top`, `_hcrit_margin`, `_bolton_lcl_temp_k`, konstanter |
| `termik/config.py` | +dew_point_2m, 950/900/800/600 hPa temperatures, geopotential_height_*hPa for 950-600 |
| `termik/fetch_weather.py` | +import, +level dicts, +`compute_thermal_top` kald, +thermal_top_m i payload (grid top-level, airfield i data-dict) |
| `termik/tests/test_scoring.py` | +14 nye thermal_top tests |
| `termik/tests/test_fetch_weather.py` | +2 nye integrationstests |
| `termik/output/app.js` | +THERMAL_TOP_STOPS, thermalTopToRgb, buildThermalTopCanvas, _drawLabels, _smoothing, setupLayerControls, updateLegend |
| `termik/output/index.html` | +#layer-section med radioknapper |
| `termik/output/style.css` | +#layer-section + mobil-regler + legend |
| `termik/output/sw.js` | CACHE_VERSION v12 → v13 |

## Test-resultat

Før: 158 tests grønne.
Efter: 174 tests grønne (+16). Ingen regression.

## Kendte begrænsninger

- `score_lapse_rate` bruger fortsat `(T_2m - T_850)/15` mens `thermal_top_m` bruger fuld parcel-teori. Inkonsistens kan opstå (lapse_rate-score 8 men thermal_top_m=0 ved lav inversion under 850 hPa). Dokumenteret som kendt feature i popup.
- `thermal_top_m` er **timevis** — brugeren navigerer time-slider for at finde dagens peak (typisk kl. 13-15). Et fremtidigt `thermal_top_max_today_m`-felt kan overvejes.
- Hcrit-margin er SW-skaleret empirisk approksimation; klassisk RASP bruger fuld surface heat flux. Vores fejl ±100-200 m.
