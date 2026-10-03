#!/usr/bin/env python3
"""Build the Monday call-list workbook from merged research JSON.

Inputs (same dir):
  enriched.json       -> list of company dicts (workflow ENRICH schema, plus 'region')
  verifications.json  -> list of verification dicts (workflow VERIFY schema)
  already_touched.json-> list of {name, domain, county, status}
  pain_offer.json     -> optional list of {pain, evidence, what_ann_fixes, offer, price_anchor}
Output: path given as argv[1]
"""
import json, re, sys, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'FL_HVAC_Call_List.xlsx')

def load(name, default):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)

enriched = load('enriched.json', [])
verifs = load('verifications.json', [])
touched = load('already_touched.json', [])
pain_offer = load('pain_offer.json', [])
overrides = load('overrides.json', {})

def norm(s):
    s = (s or '').lower()
    s = re.sub(r'\b(inc|llc|corp|corporation|co|company|the|of|and|&)\b', '', s)
    return re.sub(r'[^a-z0-9]', '', s)

# ---- merge verification into enriched ----
vmap = {}
for v in verifs:
    vmap.setdefault(norm(v.get('name')), v)

COUNTY_ORDER = {'broward': 0, 'palm beach': 1, 'miami-dade': 2, 'miami dade': 2}
TIER_ORDER = {'A': 0, 'B': 1, 'C': 2, 'X': 3}
CONF_ORDER = {'high': 0, 'medium': 1, 'med': 1, 'low': 2}

def clean(s):
    if s is None:
        return ''
    if isinstance(s, (list, tuple)):
        return '\n'.join(str(x) for x in s if x)
    return str(s).strip()

rows = []
seen = set()
for c in enriched:
    key = norm(c.get('name'))
    if not key or key in seen:
        continue
    seen.add(key)
    v = vmap.get(key, {})
    tier = clean(c.get('fit_tier')).upper()[:1] or '?'
    county = clean(c.get('county'))
    phone = clean(c.get('phone'))
    owner = clean(c.get('owner_name'))
    title = clean(c.get('owner_title'))
    address = clean(c.get('address'))
    ps = clean(v.get('phone_status')).lower()
    os_ = clean(v.get('owner_status')).lower()
    as_ = clean(v.get('address_status')).lower()
    # apply corrections from the verifier when it found a mismatch
    if 'mismatch' in ps and clean(v.get('phone_correct')):
        phone = f"{clean(v.get('phone_correct'))} (verifier corrected; researcher had {clean(c.get('phone'))})"
    if 'mismatch' in os_ and clean(v.get('owner_correct')):
        owner = f"{clean(v.get('owner_correct'))} (verifier corrected; researcher had {clean(c.get('owner_name'))})"
        if clean(v.get('owner_title_correct')):
            title = clean(v.get('owner_title_correct'))
    if 'mismatch' in as_ and clean(v.get('address_correct')):
        address = f"{clean(v.get('address_correct'))} (verifier corrected)"
    # fill blanks the verifier was able to supply
    if not owner and clean(v.get('owner_correct')) and 'unverif' not in os_:
        owner = f"{clean(v.get('owner_correct'))} (found by verifier)"
        if clean(v.get('owner_title_correct')): title = clean(v.get('owner_title_correct'))
    if not phone and clean(v.get('phone_correct')) and 'unverif' not in ps:
        phone = f"{clean(v.get('phone_correct'))} (found by verifier)"
    if not address and clean(v.get('address_correct')) and 'unverif' not in as_:
        address = clean(v.get('address_correct'))
    if 'unverif' in os_ and clean(v.get('owner_correct')) and not owner:
        owner = f"UNVERIFIED: {clean(v.get('owner_correct'))[:160]}"
    ov = overrides.get(clean(c.get('name')), {})
    if ov.get('note'):
        v = dict(v); v['extra_findings'] = (ov['note'] + ' | ' + clean(v.get('extra_findings'))).strip(' |')
    verified = ''
    if v:
        verified = f"Phone: {clean(v.get('phone_status')) or '?'} | Owner: {clean(v.get('owner_status')) or '?'} | Independent: {clean(v.get('independent_status')) or '?'}"
    ind = clean(v.get('independent_status')).lower()
    # downgrade only on an explicit positive finding, never on "no PE/franchise hits" wording
    not_indep = (ind.startswith('not independent') or ind.startswith('mismatch')
                 or re.search(r'\b(is|now|was) (pe[- ]backed|a franchise|franchise[- ]owned|consolidator[- ]owned|owned by)', ind) is not None
                 or re.search(r'\bacquired by\b', ind) is not None)
    if tier in ('A', 'B') and not_indep:
        tier = 'X'
        c['fit_reason'] = 'Verifier found PE/franchise/acquired ownership. ' + clean(c.get('fit_reason'))
    grant = 'Yes - CareerSource Broward (90%)' if county.lower().startswith('broward') else ('Check CareerSource ' + county if county else '')
    rows.append({
        'tier': tier,
        'company': clean(c.get('name')),
        'owner': owner,
        'title': title,
        'phone': phone,
        'phone_alt': clean(c.get('phone_alt')),
        'city': clean(c.get('city')),
        'county': county,
        'address': address,
        'website': clean(c.get('website')),
        'email': clean(c.get('email')),
        'second_contact': clean(c.get('second_contact')),
        'size': clean(c.get('size_estimate')),
        'founded': clean(c.get('year_founded')),
        'services': clean(c.get('services')),
        'ownership': clean(c.get('ownership')),
        'reviews': (clean(c.get('google_rating')) + (' / ' if clean(c.get('google_rating')) and clean(c.get('google_reviews')) else '') + clean(c.get('google_reviews'))).strip(),
        'software': clean(c.get('software_detected')),
        'booking': clean(c.get('online_booking')),
        'license': clean(c.get('license_on_site')),
        'hiring': clean(c.get('hiring_now')),
        'leaks': clean(c.get('observable_leaks')),
        'service': clean(c.get('recommended_service')),
        'hook': clean(c.get('call_hook')),
        'fit_reason': clean(c.get('fit_reason')),
        'confidence': clean(c.get('confidence')),
        'verified': verified,
        'extra': clean(v.get('extra_findings')),
        'grant': grant,
        'sources': clean(c.get('sources')),
        'owner_source': clean(c.get('owner_source_url')),
    })

def sort_key(r):
    return (TIER_ORDER.get(r['tier'], 9), COUNTY_ORDER.get(r['county'].lower(), 5), CONF_ORDER.get(r['confidence'].lower(), 3), r['company'].lower())

rows.sort(key=sort_key)

# ---- styles ----
FONT = 'Arial'
base = Font(name=FONT, size=10)
bold = Font(name=FONT, size=10, bold=True)
hdr_font = Font(name=FONT, size=10, bold=True, color='FFFFFF')
hdr_fill = PatternFill('solid', fgColor='0B2447')      # navy
tierA_fill = PatternFill('solid', fgColor='E2F0D9')
tierB_fill = PatternFill('solid', fgColor='FFF2CC')
input_fill = PatternFill('solid', fgColor='FFFFCC')
thin = Side(style='thin', color='D9D9D9')
border = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical='top')

def write_table(ws, headers, data, widths, input_cols=()):
    ws.append(headers)
    for i, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=i)
        cell.font = hdr_font; cell.fill = hdr_fill; cell.alignment = Alignment(wrap_text=True, vertical='center'); cell.border = border
    for r in data:
        ws.append(r)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(headers)):
        for cell in row:
            cell.font = base; cell.alignment = wrap; cell.border = border
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = 'D2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(ws.max_row, 2)}"
    for col in input_cols:
        for rr in range(2, ws.max_row + 1):
            ws.cell(row=rr, column=col).fill = input_fill

wb = Workbook()

# ---------------- Sheet 1: Monday Call List (Tier A + B) ----------------
ws = wb.active
ws.title = 'Call List Monday'
headers = ['#', 'Tier', 'Company', 'Owner / Decision Maker', 'Title', 'Phone', 'Alt Phone', 'City', 'County',
           'What They Need (service)', 'Opening Line (say this)', 'Observable Leaks (why them)', 'Verified?',
           'Grant Eligible?', 'Size', 'Founded', 'Website', 'Email', 'Address', 'Reviews (rating / count)',
           'Software Seen', 'Online Booking?', 'License # on Site?', 'Hiring?', 'Verifier Notes',
           'Called? (Y/N)', 'Outcome', 'Next Step', 'Follow-up Date', 'My Notes']
call_rows = [r for r in rows if r['tier'] in ('A', 'B')]
data = []
for i, r in enumerate(call_rows, 1):
    data.append([i, r['tier'], r['company'], r['owner'], r['title'], r['phone'], r['phone_alt'], r['city'], r['county'],
                 r['service'], r['hook'], r['leaks'], r['verified'], r['grant'], r['size'], r['founded'], r['website'],
                 r['email'], r['address'], r['reviews'], r['software'], r['booking'], r['license'], r['hiring'], r['extra'],
                 '', '', '', '', ''])
widths = [5, 6, 30, 24, 16, 18, 16, 16, 12, 24, 48, 44, 30, 22, 14, 10, 28, 24, 32, 14, 18, 12, 12, 14, 36, 10, 18, 24, 14, 30]
write_table(ws, headers, data, widths, input_cols=(26, 27, 28, 29, 30))
last = ws.max_row
# tier shading
ws.conditional_formatting.add(f"A2:AD{max(last,2)}", FormulaRule(formula=['$B2="A"'], fill=tierA_fill))
ws.conditional_formatting.add(f"A2:AD{max(last,2)}", FormulaRule(formula=['$B2="B"'], fill=tierB_fill))
# outcome dropdown
dv = DataValidation(type='list', formula1='"Voicemail,Spoke - Gatekeeper,Spoke - Owner,Booked Leak Check,Send Info,Call Back,Not Interested,Wrong Number"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f"AA2:AA{max(last, 200)}")
dv2 = DataValidation(type='list', formula1='"Y,N"', allow_blank=True)
ws.add_data_validation(dv2); dv2.add(f"Z2:Z{max(last, 200)}")

# ---------------- Sheet 2: All Prospects ----------------
ws2 = wb.create_sheet('All Prospects')
headers2 = ['Tier', 'Company', 'County', 'City', 'Owner / Decision Maker', 'Title', 'Phone', 'Website', 'Fit Reason',
            'What They Need', 'Observable Leaks', 'Confidence', 'Ownership', 'Size', 'Founded', 'Services', 'Reviews',
            'Software Seen', 'Verified?', 'Verifier Notes', 'Owner Source', 'Sources']
data2 = [[r['tier'], r['company'], r['county'], r['city'], r['owner'], r['title'], r['phone'], r['website'], r['fit_reason'],
          r['service'], r['leaks'], r['confidence'], r['ownership'], r['size'], r['founded'], r['services'], r['reviews'],
          r['software'], r['verified'], r['extra'], r['owner_source'], r['sources']] for r in rows]
write_table(ws2, headers2, data2, [6, 30, 12, 16, 24, 16, 18, 28, 40, 24, 44, 10, 16, 14, 10, 24, 14, 18, 30, 36, 30, 40])
ws2.freeze_panes = 'C2'
l2 = ws2.max_row
ws2.conditional_formatting.add(f"A2:V{max(l2,2)}", FormulaRule(formula=['$A2="A"'], fill=tierA_fill))
ws2.conditional_formatting.add(f"A2:V{max(l2,2)}", FormulaRule(formula=['$A2="B"'], fill=tierB_fill))

# ---------------- Sheet 3: Already Touched ----------------
ws3 = wb.create_sheet('Already Touched')
headers3 = ['Company', 'County', 'Website', 'Status / History', 'Monday Action']
def action_for(t):
    s = t['status'].lower()
    if 'active proposal' in s: return 'Do NOT cold call. Confirm the Mon Oct 5 Google Meet (10am or 6pm) and bring the 3 clarifying questions.'
    if 'past client' in s: return 'Call Cornel/Maurice/Kimroy: ask for a 2-line testimonial + 2 referrals to AC owners they know. Offer to write it for them.'
    if 'notion tier 1' in s: return 'Call. Named owner known. Lead with the FMBS story; ask for a 20-min Leak Check.'
    if 'notion tier 2' in s: return 'Call the office line; ask who runs operations/training. Large shop: pitch Team Training (grant) first.'
    if 'bounced' in s: return 'Email never arrived. Phone is the only touch they have had. Call fresh.'
    if 'no reply' in s: return 'Call: "I emailed in June about AI training; that was the wrong pitch. What I actually do is rebuild the office systems..."'
    return 'Call.'
data3 = [[t['name'], t.get('county', ''), t.get('domain', ''), t['status'], action_for(t)] for t in touched]
write_table(ws3, headers3, data3, [36, 12, 26, 70, 70])
ws3.freeze_panes = 'B2'

# ---------------- Sheet 4: Pain -> Offer ----------------
ws4 = wb.create_sheet('Pain to Offer Map')
headers4 = ['HVAC Owner Pain Point', 'Evidence / Numbers', 'What Ann Fixes', 'Offer', 'Price Anchor', 'Phone Hook']
data4 = [[p.get('pain', ''), p.get('evidence', ''), p.get('what_ann_fixes', ''), p.get('offer', ''), p.get('price_anchor', ''), p.get('hook', '')] for p in pain_offer]
write_table(ws4, headers4, data4, [30, 48, 44, 26, 22, 48])
ws4.freeze_panes = 'B2'

# ---------------- Sheet 4b: More Leads (discovered, not individually researched) ----------------
discovered = load('discovered.json', [])
ws4b = wb.create_sheet('More Leads (unverified)')
headers4b = ['Company', 'City', 'County', 'Phone (from snippet)', 'Website', 'Reviews', 'Why it surfaced (signal)', 'Found via', 'Source URL']
seen_d = set(seen) | {norm(t['name']) for t in touched}
data4b = []
for c in discovered:
    k = norm(c.get('name'))
    if not k or k in seen_d:
        continue
    seen_d.add(k)
    data4b.append([clean(c.get('name')), clean(c.get('city')), clean(c.get('county')), clean(c.get('phone')), clean(c.get('website')),
                   clean(c.get('review_count')), clean(c.get('signal')), clean(c.get('angle')).replace('discover:', ''), clean(c.get('source_url'))])
# phone-bearing, strong-signal rows first
def d_key(r):
    s = (r[6] or '').lower()
    strong = any(w in s for w in ('strong fit', 'hiring', 'scaling', 'owner', 'founder', 'merger', 'acquired', 'new owner', 'second'))
    return (0 if r[3] else 1, 0 if strong else 1, COUNTY_ORDER.get((r[2] or '').lower(), 5), r[0].lower())
data4b.sort(key=d_key)
write_table(ws4b, headers4b, data4b, [32, 16, 12, 18, 28, 10, 60, 18, 40])
ws4b.freeze_panes = 'B2'

# ---------------- Sheet 5: Scoreboard (formulas) ----------------
ws5 = wb.create_sheet('Scoreboard')
ws5['A1'] = 'Weekly Scoreboard (auto-counts from Call List Monday)'; ws5['A1'].font = Font(name=FONT, size=12, bold=True)
labels = [
    ('Tier A prospects', "=COUNTIF('Call List Monday'!B:B,\"A\")"),
    ('Tier B prospects', "=COUNTIF('Call List Monday'!B:B,\"B\")"),
    ('Calls made (Called? = Y)', "=COUNTIF('Call List Monday'!Z:Z,\"Y\")"),
    ('Spoke to owner', "=COUNTIF('Call List Monday'!AA:AA,\"Spoke - Owner\")"),
    ('Leak Checks booked', "=COUNTIF('Call List Monday'!AA:AA,\"Booked Leak Check\")"),
    ('Call backs owed', "=COUNTIF('Call List Monday'!AA:AA,\"Call Back\")"),
    ('Voicemails left', "=COUNTIF('Call List Monday'!AA:AA,\"Voicemail\")"),
    ('Not interested', "=COUNTIF('Call List Monday'!AA:AA,\"Not Interested\")"),
    ('Wrong numbers (fix in list)', "=COUNTIF('Call List Monday'!AA:AA,\"Wrong Number\")"),
    ('Owner-contact rate', "=IFERROR(B5/B4,0)"),
    ('Booking rate (of owner conversations)', "=IFERROR(B6/B5,0)"),
]
r0 = 3
ws5.cell(row=r0 - 1, column=1, value='Metric').font = bold
ws5.cell(row=r0 - 1, column=2, value='Value').font = bold
for i, (lab, f) in enumerate(labels):
    ws5.cell(row=r0 + i, column=1, value=lab).font = base
    c = ws5.cell(row=r0 + i, column=2, value=f); c.font = base
    if 'rate' in lab:
        c.number_format = '0.0%'
ws5.cell(row=r0 + len(labels) + 1, column=1, value='Weekly target (from the 30-day plan): 25 touches, 3+ owner conversations, 1+ Leak Check booked per week.').font = Font(name=FONT, size=9, italic=True)
ws5.cell(row=r0 + len(labels) + 2, column=1, value='Legend: yellow cells on "Call List Monday" (Called?, Outcome, Next Step, Follow-up Date, My Notes) are yours to fill in. Everything else was researched Oct 2-3, 2026 from public search results (company-site snippets, BBB principals, Yelp/Google review counts, LinkedIn snippets, chamber directories, job boards); sources are listed per row on "All Prospects". "More Leads (unverified)" holds companies that surfaced in discovery but were not individually researched: confirm phone and owner before relying on a row.').font = Font(name=FONT, size=9, italic=True)
ws5.cell(row=r0 + len(labels) + 3, column=1, value='Example of a filled row: Called? = Y, Outcome = Booked Leak Check, Next Step = "Tue 7:30am Leak Check, send Calendly link", Follow-up Date = 10/6/2026.').font = Font(name=FONT, size=9, italic=True)
ws5.column_dimensions['A'].width = 44; ws5.column_dimensions['B'].width = 14

from openpyxl.workbook.properties import CalcProperties
wb.calculation = CalcProperties(fullCalcOnLoad=True)
wb.save(OUT)
print(json.dumps({'out': OUT, 'enriched': len(enriched), 'rows': len(rows), 'call_list': len(call_rows),
                  'tiers': {t: sum(1 for r in rows if r['tier'] == t) for t in 'ABCX'}, 'verified': len(verifs), 'touched': len(touched)}))
