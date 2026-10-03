# First-client package (Oct 2026)

Built for Ann Kelly / ClearFrequency.ai to land the first paid HVAC engagement in South Florida.

| File | What it is |
|---|---|
| `FL_HVAC_Call_List.xlsx` | The Monday call list. Tabs: **Call List Monday** (Tier A + B, with owner, phone, opening line), **All Prospects** (everything researched, incl. not-a-fit and why), **Already Touched** (Bee Cool, FMBS, Paradise, Art, June cold emails), **Pain to Offer Map**, **Scoreboard** (auto-counts your outcomes). |
| `FIRST-CLIENT-PLAYBOOK.md` | The path: offer ladder and prices, pain points in the owner's words, Monday minute-by-minute, phone script, voicemail, text, email, objections, the Leak Check call, and the 30-day plan. |
| `research/pain-points-south-florida.md` | Ranked pain points with numbers and sources, South Florida specifics (PE roll-ups, permits, 489.119, wages, refrigerant). |
| `research/owner-language.md` | What owners actually say, phrase bank, top objections and answers, when to call. |
| `research/competition-pricing-grants.md` | Who else sells this, price benchmarks, CareerSource grant rules, the license-number compliance hook. |
| `research/prospect-data/` | Raw JSON from the prospect research runs (discovered candidates, enriched records, verification notes) so the sheet can be rebuilt or extended. |

What is in the list (as of Oct 3, 2026): 90 companies individually researched (60 Broward, 30 Palm Beach + Miami-Dade), 56 of them Tier A or B on the Monday call list (22 A, 34 B), 57 re-checked by a second verification pass, 3 excluded as consolidator-owned or out of area, plus 424 additional leads from discovery on the "More Leads (unverified)" tab and the 16 companies already contacted.

How the list was built: ~120 seed companies from Apollo's free company lookup (Broward, Palm Beach, Miami-Dade; 6-100 employees; HVAC keywords), plus web sweeps by city, chamber directory, transition signals (mergers, hiring, new businesses) and weak-web-presence signals. Each company was then researched from public search results (company site snippets, BBB principals, Yelp/Google review counts, LinkedIn snippets, news) and Tier A/B contact data was re-checked by a second pass against different sources. Direct website fetches were blocked in the research environment, so "online booking" and "license on site" fields are only filled where a search snippet showed them; the rest is marked unknown rather than guessed.

Related: `marketing/hvac/strategy/offer-and-audit-framework.md` and `marketing/hvac/strategy/30-day-first-client-plan.md` (the original plan this executes), `marketing/hvac/research/hvac-market-research.md`.
