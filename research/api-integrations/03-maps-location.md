# 03 — Maps, Places, and Walk Times

> Research subagent **A3** for the BryantPathfinder API swarm. Scope: replace Pathfinder's manually-maintained 11-minute walk-time buffer with real distance data, and surface campus-life context (weather, dining, parking) on the schedule page. Pilot scale assumed: ~50 students at Bryant, moderate use (each student generates ~3 schedule renders per session, ~5 sessions per registration cycle, ~750 total schedule renders).

---

## 1. Where Pathfinder is today

The current product carries a hand-curated table of building-to-building walking times that triggers an **11-minute buffer warning** when two consecutive classes are in different buildings. This was a hackathon shortcut. Bryant's academic core is compact (Unistructure, Bello, Koffler, BELC, MRC, Smithfield, Fisher) — most pairs are 4–7 minutes. The 11-minute number is a worst-case estimate calibrated to BELC ↔ Smithfield (the longest non-residential pair on the academic side), so it errs on the conservative side and produces a meaningful number of false positives.

Bryant's official campus map now redirects from `campusmap.bryant.edu` to **Esri ArcGIS Experience Builder** (`experience.arcgis.com/experience/e012543a266348cd84bc5e9b6dba632e`). This matters for two reasons:

1. The map is **not** Concept3D, despite being a common vendor in higher-ed; previous links to a Concept3D instance (`cms.concept3d.com/map/accessible.php?id=1164`) appear to be deprecated or used only for accessibility fallback.
2. ArcGIS Online provides a free developer tier (basemaps, geocoding, routing) that could theoretically slot in — although Pathfinder doesn't need a polished campus map vendor, it needs lat/long for ~30 buildings and walking times.

Sources:
- [Bryant University Campus Map (ArcGIS)](https://experience.arcgis.com/experience/e012543a266348cd84bc5e9b6dba632e)
- [Campus Maps – Bryant Information Services](https://is.bryant.edu/services/communication-and-collaboration/web-services/campus-maps)
- [Concept3D Bryant accessibility map](https://cms.concept3d.com/map/accessible.php?id=1164&cId=64880&mId=651515)

---

## 2. Google Maps Platform

### 2a. Critical pricing change — March 2025

The single biggest update for any agent reading this in 2026: **the universal $200/month free credit was discontinued on February 28, 2025** and replaced with per-SKU free usage caps. Each Core Services SKU now has its own monthly free allotment based on tier:

- **Essentials** SKUs (Static Maps, Dynamic Maps, Geocoding): **10,000 free events/month** per SKU.
- **Pro** SKUs (Distance Matrix, Routes Pro/traffic-aware, Places): **5,000 free events/month** per SKU.
- **Enterprise** SKUs (advanced routing, two-wheel routing, route optimization): **1,000 free events/month** per SKU.

Free tiers no longer pool, which is a meaningful change for low-volume apps that used to spread the $200 credit across several APIs. For Pathfinder at 50-student pilot scale, **every individual API call we make almost certainly stays inside its free SKU envelope**.

Sources:
- [Google Maps Platform pricing overview](https://developers.google.com/maps/billing-and-pricing/overview)
- [Changes to Google Maps Platform automatic volume discounts, monthly credit, and services transitioning to Legacy status](https://developers.google.com/maps/billing-and-pricing/faq)
- [Google Maps Platform March 2025 changes](https://developers.google.com/maps/billing-and-pricing/march-2025)
- [9to5Google: Google Maps Platform expanding free usage limits for developers](https://9to5google.com/2024/12/09/google-maps-platform-usage-limits/)

### 2b. Distance Matrix API — the obvious fit for walk-time replacement

- **Pricing:** $5.00 per 1,000 elements (origin × destination pairs); Advanced Distance Matrix with traffic is $10.00 per 1,000.
- **Free tier:** Pro SKU, 5,000 elements/month free.
- **Auth:** API key + restrictions (HTTP referrer or IP).
- **Status:** Now branded "Distance Matrix API (Legacy)"; Google steers new development to **Routes API → Compute Route Matrix**, which is the same capability rebranded.

For Pathfinder's use case the math is very forgiving. With 30 buildings, the full B→B walking matrix is 30×29 = 870 elements computed **once**, cached forever. Even if we recompute monthly to capture seasonal walking-path closures, lifetime API spend is effectively zero.

Sources:
- [Distance Matrix API (Legacy) Usage and Billing](https://developers.google.com/maps/documentation/distance-matrix/usage-and-billing)
- [Routes API Usage and Billing](https://developers.google.com/maps/documentation/routes/usage-and-billing)
- [Google Maps Platform core services pricing list](https://developers.google.com/maps/billing-and-pricing/pricing)

### 2c. Routes API — turn-by-turn for first-week navigation

- **Compute Routes (Essentials/Basic):** $5.00/1,000 requests, max 10 intermediate waypoints.
- **Compute Routes (Pro/traffic-aware):** $10.00/1,000.
- **Free tier:** 5,000 events/month for Pro; 10,000 for Essentials.

Marginal value over Distance Matrix is small for Pathfinder. Walking on a 1,400-acre campus does not need turn-by-turn — students already use Apple/Google Maps if they actually need it. A Routes API integration would only matter if we ship a mobile companion app, which is out of scope.

### 2d. Places API — dining halls, library, study spots

- **Place Details (Pro):** ~$17/1,000 requests; Place Details Essentials ~$5/1,000.
- **Free tier:** 5,000 Pro events/month.
- **Auth:** API key.

Pathfinder could hydrate "between-class context" (e.g., "you have 75 minutes between FIN 310 and MGT 220 — Salmanson Dining Hall is open until 14:00"). For 50 students that's a trivial number of calls. **But Bryant-specific data — dining hall hours, library zone status, lab open hours — is not consistently in Google Places.** A hand-curated `bryant_places.json` (15–20 entries) would be more accurate than the Places API for Bryant's specific buildings.

### 2e. Static Maps API — embed campus map in schedule view

- **Pricing:** $2.00/1,000 loads (Essentials).
- **Free tier:** 10,000/month.
- **Use case:** Render a small map thumbnail on each schedule card showing pinned buildings for that schedule.

This is the cheapest, highest-ratio Google product for Pathfinder. A schedule with five buildings = one Static Maps call. 50 students × 5 sessions × 3 schedules = 750 loads/month, miles below the free cap.

Source: [Maps Static API Usage and Billing](https://developers.google.com/maps/documentation/maps-static/usage-and-billing)

### 2f. Geocoding API

- **Pricing:** $5/1,000 (Essentials).
- **Free tier:** 10,000/month.
- **Use case:** One-time, for the Bryant building address list. Effectively free.

---

## 3. Mapbox

- **Free tier:** 50,000 map loads/month for web; 25,000 monthly active users (MAU) for mobile. Static Images API has its own free quota (historically 50,000/month).
- **Matrix API:** counted as billable requests under the routing tier; Mapbox tends to undercut Google by ~15–25% at volume but the free tier is what matters here.
- **Auth:** Public access tokens (URL-restricted) + secret tokens for server-side.
- **Strength:** Best-in-class custom map styling. If Pathfinder ever ships a polished campus visualization, Mapbox is the right vendor — warmer, more designable than Google's stock tiles, fits the editorial-minimalism aesthetic better than Google's blue-and-grey defaults.
- **Weakness:** Walking-time accuracy is reportedly slightly worse than Google for short pedestrian links because Mapbox's pedestrian graph in the US is sparser than Google's footpath data on private campuses.

Sources:
- [Mapbox Pricing](https://www.mapbox.com/pricing)
- [Mapbox pricing by products](https://docs.mapbox.com/accounts/guides/pricing/)
- [Maps API Pricing Comparison: Google Maps vs Mapbox](https://www.buildmvpfast.com/api-costs/maps)

---

## 4. OpenStreetMap / Overpass API

- **Cost:** Free.
- **Auth:** None.
- **Limits:** Soft rate limiting (default 180s max query, 512MiB memory; servers are under heavy load and tarpit aggressive users). The OSMF API usage policy is explicit that the public Overpass instance is **not** for production user-facing applications.
- **Quality on Bryant:** OSM has Bryant building footprints — Unistructure, Koffler, Bello, etc. are tagged with names. Footpath coverage is partial. Useful for one-off bulk extraction of building shapes/coordinates, **not** for live walking-time queries.

The right pattern: use Overpass **once** to extract Bryant building polygons and centroids, snapshot to JSON, stop calling it. Combining this with OSRM (self-hosted on the OSM road graph) would give us free, unlimited routing — but operating a routing server is overhead a 50-student pilot doesn't need.

Sources:
- [OpenStreetMap API usage policy](https://wiki.openstreetmap.org/wiki/API_usage_policy)
- [Overpass API documentation](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [OSMF Operations Working Group API policy](https://operations.osmfoundation.org/policies/api/)

---

## 5. HERE Maps

- **Free tier:** 250,000 transactions/month on the freemium plan, then $1/1,000.
- **Routing API (car/bike/pedestrian):** First 30,000 free, then $0.75/1,000.
- **Advanced routing** (transit, intermodal, time-aware): First 5,000 free, then $2.50/1,000.
- **Auth:** API key + app credentials.
- **Pedestrian quality:** Generally on par with Google in dense urban areas; less specifically tuned to college-campus footpaths than Google Maps.

HERE is the clear price-leader if Pathfinder ever scales to 5,000+ students per institution and starts billing for routing volume. At 50-student pilot scale the volume difference is irrelevant.

Sources:
- [HERE Base Plan pricing](https://www.here.com/get-started/pricing)
- [HERE Maps API Pricing: Costs, Free Tier, and Examples (2026 Guide)](https://local-eyes.nl/here-maps-api-costs-in-2024/)

---

## 6. Foursquare Places API

- **Free tier (current):** Pay-as-you-go with $200/month in free usage credits if you sign up for a developer account; legacy free tier of 10,000 Pro calls is being changed.
- **June 1, 2026 update:** Pro endpoints drop to **500 free calls/month**; rates restructured. Checkins, lists, tastes, tips, users endpoints remain free.
- **Strength over Google Places:** Tag-rich metadata ("study spot", "open late", "wifi", "quiet"). For a category like "where can I work between my 11am and 2pm classes near Unistructure" Foursquare's tag taxonomy is genuinely better.
- **Weakness for Bryant:** Bryant's campus interior places (Bello dining, library zones, BELC lounges) are not consistently in Foursquare. The tag advantage applies mostly to commercial venues.

Sources:
- [Foursquare Pricing](https://foursquare.com/pricing/)
- [Foursquare upcoming changes](https://docs.foursquare.com/developer/reference/upcoming-changes)
- [Heads up developers: With FSQ/Places API, you can now "pay as you go"](https://foursquare.com/resources/blog/news/heads-up-developers-with-fsq-places-api-you-can-now-pay-as-you-go/)

---

## 7. Open-Meteo (weather)

- **Cost:** Free for non-commercial use, **no API key, no registration**.
- **Limits:** <10,000 calls/day, <5,000/hour, <600/minute on the free public endpoint.
- **Commercial use:** Subscription required if Pathfinder monetizes (which it doesn't yet, but commercialization is the swarm context).
- **Capabilities:** Hyperlocal forecast up to 14 days; hourly precipitation probability; perfect for "rain expected Wednesday 11am — plan for the indoor walkway between Unistructure and Koffler."

Open-Meteo is the obvious choice for the weather-aware walk-time UX feature. The integration is one HTTPS call: `GET https://api.open-meteo.com/v1/forecast?latitude=41.8779&longitude=-71.5347&hourly=precipitation_probability,temperature_2m,wind_speed_10m`. No auth, no SDK, no billing. The commercial license question can be deferred until Pathfinder actually has paying customers.

Sources:
- [Open-Meteo Pricing](https://open-meteo.com/en/pricing)
- [Free Open-Source Weather API – Open-Meteo](https://open-meteo.com/)
- [Open-Meteo on GitHub](https://github.com/open-meteo/open-meteo)

---

## 8. Tomorrow.io and OpenWeather (paid alternatives)

- **Tomorrow.io:** Free tier with daily/hourly/per-second rate caps; paid tiers $25–$500/month. 80 data fields including air quality, pollen, road risk, fire index.
- **OpenWeather:** Free tier of 1,000 calls/day; One Call API 3.0 has a separate free quota.

Neither offers anything Pathfinder needs that Open-Meteo doesn't already provide for free. **Skip both** unless commercial licensing forces the question.

Sources:
- [Tomorrow.io Pricing Overview](https://support.tomorrow.io/hc/en-us/articles/23554984091156-Tomorrow-io-Pricing-Overview)
- [Tomorrow.io Free API Plan Rate Limits](https://support.tomorrow.io/hc/en-us/articles/20273728362644-Free-API-Plan-Rate-Limits)
- [OpenWeather Self-Service API Pricing](https://openweathermap.org/price)

---

## 9. Bryant-specific campus data

- **Vendor:** Esri ArcGIS Experience Builder (confirmed via redirect from `campusmap.bryant.edu`).
- **Concept3D:** Apparently **not** the active vendor; legacy accessibility map only. This contradicts the swarm prompt's hypothesis. Most New England private business schools that picked a campus-map vendor in the 2018–2022 wave went Concept3D; Bryant did not.
- **Implication:** ArcGIS Location Platform's free developer tier (20,000 geocodes/month, generous routing freebies) is in-house compatible if Bryant ever wants to formally sponsor Pathfinder. That said, Bryant is unlikely to expose its ArcGIS layer to a student-built app without procurement review.

Sources:
- [ArcGIS Location Platform Pricing](https://location.arcgis.com/pricing/)
- [Concept3D Higher Education](https://concept3d.com/use-cases/higher-education/)
- [Concept3D Customized Interactive Map and Virtual Tour Pricing](https://concept3d.com/interactive-virtual-experiences/pricing/)

---

## 10. Indoor positioning (Mappedin, Pointr)

- **Mappedin Advanced:** $85/map/month (annual). **Mappedin Pro (full SDK/API):** $165/map/month (annual). Custom enterprise quotes for multi-building venues.
- **Use case:** Indoor wayfinding inside Unistructure (a giant single connected building with hundreds of rooms — this is actually a real Bryant pain point for first-year students).
- **Verdict:** Overkill for Pathfinder's current scope, but interesting commercialization story for year two. Bryant is exactly the kind of campus where indoor wayfinding has genuine value because Unistructure is one of the largest single-roof academic buildings in the country.

Sources:
- [Mappedin Pricing](https://www.mappedin.com/pricing/)
- [Mappedin University & College Campus Maps and Wayfinding](https://www.mappedin.com/industries/colleges-and-universities/)
- [University Mapping SDK – Mappedin](https://www.mappedin.com/resources/blog/wayfinding-sdk-indoor-mapping-for-universities-and-colleges/)

---

## 11. Bryant shuttle and parking

- **Shuttle service:** Bryant runs three shuttle lines (Gold Line, Bulldog Express, Tupper On-Demand). The student-facing tracker is the **My Bryant Transit (MBT)** mobile app. **No public GTFS feed could be located.** This is consistent with most small-campus internal shuttles — they often run on a vendor like Passio GO or DoubleMap with proprietary tracking, not GTFS.
- **Implication:** Real-time shuttle integration would require a vendor partnership with whoever runs MBT (likely Passio or Via). Out of scope for the pilot.
- **Parking APIs:** ParkMobile has a developer portal at `developer.parkmobile.io` but APIs are gated to commercial transportation/permit integrators, not student-facing apps. Bryant's lots are managed internally, not via ParkMobile. **No actionable API here.**

Sources:
- [Transportation – Bryant University Information Directory](https://info.bryant.edu/transportation)
- [My Bryant Transit App on the App Store](https://apps.apple.com/us/app/my-bryant-transit/id6444458409)
- [Parking and Transportation – Bryant Information Services](https://is.bryant.edu/services/administrative-and-business/parking-and-transportation)
- [ParkMobile Developer Portal](https://developer.parkmobile.io/)
- [ParkMobile Parking Technology Integrations](https://parkmobile.io/parking-providers/integrations)

---

## 12. Cost model at 50-student pilot scale

Assumptions: 50 students, 5 active sessions/student/cycle, 3 schedules generated per session, 6 buildings touched per schedule on average, one Static Map render per schedule card. Walking-time matrix is precomputed and cached.

| API | Calls/month | Free tier | Effective spend |
|---|---|---|---|
| Google Distance Matrix (one-time precompute) | 870 elements, once | 5,000/mo | $0 |
| Google Static Maps (per schedule card) | 750 | 10,000/mo | $0 |
| Google Geocoding (one-time, 30 buildings) | 30, once | 10,000/mo | $0 |
| Open-Meteo (per schedule render) | 750 | ~300,000/mo soft cap | $0 |
| Foursquare Places (optional context) | <500 | 500/mo (post-Jun 2026) | $0 |
| OpenStreetMap Overpass (one-time extraction) | ~5 | Soft, fair-use | $0 |
| **Total** | | | **$0/month** |

Even at 500 students (10× pilot), the Distance Matrix precompute pattern means the only growing line item is Static Maps, which would still be ~7,500 calls/month — comfortably free.

---

## 13. Top 3 to integrate, ranked by impact per dollar

### 1. Open-Meteo — integrate first, no caveats

Free, no auth, no rate-limit risk at our scale, and unlocks a feature the manual buffer fundamentally cannot: **weather-aware walk warnings**. "10-minute walk between Smithfield and Fisher, 70% chance of rain Wednesday at 11am" is a qualitatively better warning than "11-minute buffer." Integration is a 30-line FastAPI client. **Effort: ~2 hours. Cost: $0. Impact: high — it's a feature competitors don't have.**

### 2. Google Distance Matrix API (one-time precompute, then static)

Replace the manual 11-minute buffer with a real B→B walking-time matrix, computed **once** and stored in a JSON file alongside `sections.json`. Run it monthly via a cron-style script to capture path closures. Building list: ~30 entries; matrix size: ~870 elements; well inside the 5,000/month free Pro tier. **Effort: ~3 hours including geocoding the buildings. Cost: $0. Impact: medium-high — eliminates false-positive warnings on short walks (Unistructure ↔ Koffler is 3 minutes, not 11) and false-negative on long ones (BELC ↔ MRC is 13–14 minutes, currently understated).**

### 3. Google Static Maps API — per-schedule visualization

A small map thumbnail on each schedule card showing the buildings the student will be in that semester. Pure visual polish, but it ties the product to physical campus geography in a way that distinguishes Pathfinder from a generic class scheduler. **Effort: ~4 hours including design integration with the editorial aesthetic (warm cream + gold pins). Cost: $0. Impact: medium — pure UX, but high signal value in screenshots and demos.**

### Honorable mentions

- **Mappedin** — right answer for year two, when Pathfinder offers indoor wayfinding to first-year students inside Unistructure.
- **OSM Overpass for building polygon extraction** — useful one-time data acquisition; not a runtime dependency.
- **ArcGIS Location Platform** — interesting only if Bryant formally sponsors Pathfinder and wants to use the institution's existing Esri stack.

---

## 14. Opinion: is the manual 11-minute buffer actually worse than Distance Matrix?

**Yes, and the gap is bigger than it looks — but only on two dimensions: precision and trust.**

The manual buffer's specific failure modes:

1. **False positives.** Many adjacent-building pairs at Bryant are 3–5 minutes (Unistructure ↔ Koffler, Bello ↔ Salmanson). Flagging an 11-minute warning between an 11:00 class in Unistructure and a noon class in Koffler is wrong, and — once a student notices — undermines trust in every other warning the system shows. The current solver is biased toward conservatism, but conservatism in a UX warning system is paid for in alert fatigue.

2. **False negatives, occasionally.** BELC ↔ MRC is at the long edge of the campus academic core; a 50-minute passing window between an 11:50 class and a 1:00 class through that path with a stop at Salmanson can run 13+ minutes including doors and stairwells. A flat 11-minute buffer doesn't capture that.

3. **Weather and time of day.** January at noon is not September at 9am. Pedestrian routes that cross the central quad are slow when the Smithfield maintenance team hasn't cleared the snow on the diagonal walk yet. Weather-aware walk times — Open-Meteo + a 1.2× multiplier for precipitation — are not theoretical academic improvements; they reflect a real semester at Bryant.

4. **The product story.** "We computed real walking times for every building pair on your campus" is a sentence that converts demo viewers into users. "We have a constant" is not. For a hackathon-stage product trying to justify a pilot, the precomputed Distance Matrix is worth the engineering cost purely as a procurement/credibility artifact, even before considering accuracy gains.

That said, the manual buffer is **not** catastrophically wrong. It's a solid 80% solution. If Owen has 4 hours of engineering time before the pilot, **he should spend them on the Distance Matrix precompute and Open-Meteo integration** rather than on adding a new feature. If he has 2 hours, just do Open-Meteo — the weather signal is a more visible product win than refining a buffer that already works most of the time. If he has 1 hour, leave the buffer alone and ship something else.

**Final ranking:** Open-Meteo > Google Distance Matrix (precompute) > Google Static Maps > everything else. All three together cost $0/month at 50-student pilot scale, all three together are ~10 hours of engineering, and all three together turn "we have an 11-minute warning" into "we model your campus." That's a defensible commercialization story for the second school the pilot tries to land.
