#!/usr/bin/env python3
"""
bondcalc.py — calcolatore di portafogli di obbligazioni sovrane euro-area
(BTP / OAT / bonos), per un residente fiscale italiano che compra sul
secondario tramite broker e tiene a scadenza.

Zero dipendenze (Python 3.8+). Legge un JSON di portafoglio e produce in
markdown:
  - per ogni bond: nominale (arrotondato al lotto), rateo, esborso reale,
    YTM lordo, netto (IRR sui flussi netti), netto dopo bollo
  - mappa mese per mese: cedole nette, capitale netto, bollo stimato
  - tabella "quando recuperi i soldi"
  - totali e copertura mensile delle cedole

Uso:
  python3 bondcalc.py portafoglio.json [--settle YYYY-MM-DD] [--out report.md]

Formato JSON (campi opzionali tra parentesi):
{
  "trade": "2026-11-19",          # data ordine -> valuta T+2 lavorativi
  ("settle": "2026-11-23"),       # in alternativa: data valuta esplicita
  ("stamp_duty": 0.002),          # bollo annuo sul controvalore; 0 = off
  ("tax": 0.125),                 # aliquota titoli di Stato white list
  "bonds": [
    {"isin": "FR001400Z2L7", "name": "OAT 2,70% feb 2031",
     "coupon": 2.70, "maturity": "2031-02-25", "price": 94.89,
     "invested": 6000, "price_status": "verified",
     ("nominal": 6000),           # al posto di invested: nominale esatto
     ("frequency": 1),            # cedole/anno; default IT=2, altri=1
     ("lot": 1),                  # taglio minimo negoziabile (nominale)
     ("commission": 0)}           # commissione in € sull'ordine
  ]
}

Convenzioni (vedi references/methodology.md):
  - price = corso secco (quotazione di borsa, senza rateo).
  - Le date cedola si ricavano dalla scadenza andando indietro di
    12/frequency mesi: l'ultima cedola si paga SEMPRE alla scadenza,
    insieme al capitale.
  - BTP: semestrali. OAT, bonos, Bund, OLO, DSL...: annuali.
  - Rateo ACT/ACT (ICMA). Il compratore paga al venditore il rateo al
    netto dell'imposta (12,5%) e incassa poi la cedola intera netta.
  - Il guadagno a scadenza (100 - costo) e' tassato al 12,5% come
    reddito diverso (compensabile con minusvalenze pregresse: lo script
    NON assume crediti d'imposta). Sopra la pari la perdita genera una
    minusvalenza che lo script NON valorizza (prudente).
  - YTM: tasso effettivo annuo composto, ACT/365.
  - Bollo 0,20%/anno sul controvalore (stima: prezzo lineare verso 100),
    addebitato al 31/12 pro-rata (le banche lo addebitano di solito
    trimestralmente: l'effetto sul rendimento e' trascurabile).
"""

import argparse
import calendar
import json
import math
from datetime import date, timedelta

DEFAULT_TAX = 0.125
DEFAULT_STAMP = 0.002

NOMI_MESI = ["gen", "feb", "mar", "apr", "mag", "giu",
             "lug", "ago", "set", "ott", "nov", "dic"]


# ---------------------------------------------------------------- date utils

def add_months(d, n):
    m0 = d.month - 1 + n
    y, m = d.year + m0 // 12, m0 % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return date(y, month, day)


def is_target_holiday(d):
    if d.weekday() >= 5:
        return True
    if (d.month, d.day) in {(1, 1), (5, 1), (12, 25), (12, 26)}:
        return True
    e = easter(d.year)
    return d in (e - timedelta(days=2), e + timedelta(days=1))


def add_business_days(d, n):
    while n > 0:
        d += timedelta(days=1)
        if not is_target_holiday(d):
            n -= 1
    return d


def month_label(y, m):
    return f"{NOMI_MESI[m - 1]} {y}"


# ---------------------------------------------------------------- finance

def irr(flows, t0):
    """Tasso effettivo annuo (ACT/365) che azzera il VAN dei flussi
    [(date, amount)] (esborsi negativi). Bisezione robusta."""
    def npv(r):
        return sum(a / (1 + r) ** ((d - t0).days / 365.0) for d, a in flows)
    lo, hi = -0.9, 1.0
    if npv(lo) * npv(hi) > 0:
        return float("nan")
    for _ in range(300):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def default_frequency(isin):
    return 2 if isin.upper().startswith("IT") else 1


def default_lot(isin):
    # BTP su MOT: 1.000 nominali. OAT: taglio 1 € (ma il broker puo'
    # imporre lotti maggiori: specificare "lot" nel JSON). Bonos: 1.000.
    i = isin.upper()
    if i.startswith("FR"):
        return 1
    return 1000


def coupon_schedule(settle, maturity, freq):
    """Ritorna (prev_coupon_date, [date cedola future > settle]),
    generate all'indietro dalla scadenza."""
    step = 12 // freq
    future = []
    k = 0
    while True:
        d = add_months(maturity, -step * k)
        if d <= settle:
            return d, sorted(future)
        future.append(d)
        k += 1


def analyze(bond, settle, tax, stamp):
    warn = []
    isin = bond["isin"]
    mat = date.fromisoformat(bond["maturity"])
    clean = float(bond["price"])
    coupon = float(bond.get("coupon", 0.0))
    invested = float(bond.get("invested", 0.0))
    if "nominal" not in bond and invested <= 0:
        raise ValueError(f"{isin}: serve 'invested' (€ da spendere) o 'nominal'")
    freq = int(bond.get("frequency", default_frequency(isin)))
    lot = float(bond.get("lot", default_lot(isin)))
    commission = float(bond.get("commission", 0.0))

    if freq not in (1, 2, 4, 12):
        raise ValueError(f"{isin}: frequency deve essere 1, 2, 4 o 12")
    if mat <= settle:
        raise ValueError(f"{isin}: scadenza {mat} non successiva alla valuta {settle}")

    prev, cdates = coupon_schedule(settle, mat, freq)
    cpn_per_stacco = coupon / freq  # per 100 nominale, lordo
    nxt = cdates[0]
    accrued = cpn_per_stacco * (settle - prev).days / (nxt - prev).days if coupon else 0.0

    # Esborso per 100 nominale: secco + rateo al netto della ritenuta
    unit_cash = (clean + accrued * (1 - tax)) / 100.0
    if "nominal" in bond:
        nom_raw = nom = float(bond["nominal"])
        if abs(nom / lot - round(nom / lot)) > 1e-9:
            warn.append(f"nominale {nom:,.0f} non multiplo del lotto {lot:,.0f}.")
        invested = nom * unit_cash + commission
    else:
        nom_raw = max(0.0, invested - commission) / unit_cash
        # lotto piu' vicino al budget (puo' superarlo di meno di mezzo lotto)
        nom = max(lot, math.floor(nom_raw / lot + 0.5) * lot)
    if nom <= 0:
        raise ValueError(f"{isin}: importo insufficiente per un lotto da {lot:g}")
    cash_out = nom * unit_cash + commission
    leftover = invested - cash_out

    # coupon_months: solo controllo di coerenza (le date vengono dalla scadenza)
    cm = bond.get("coupon_months")
    real_months = sorted({d.month for d in
                          (add_months(mat, -(12 // freq) * k) for k in range(freq))})
    if cm is not None and sorted(int(x) for x in cm) != real_months:
        warn.append(f"`coupon_months` {cm} ignorato: con scadenza {mat.isoformat()} "
                    f"e {freq} cedola/e l'anno i mesi di stacco sono {real_months}. "
                    f"Se il prospetto dice altro, correggi `maturity` o `frequency`.")
    if clean > 100:
        warn.append(f"prezzo {fmt(clean)} sopra la pari: a scadenza perdita di "
                    f"{fmt(clean - 100)} per 100 (minusvalenza non valorizzata qui).")
    if bond.get("price_status") != "verified":
        warn.append("prezzo stimato: tutti i numeri di questo titolo sono stime.")
    if lot > 1 and abs(leftover) > 0.005 and "nominal" not in bond:
        what = (f"restano {fmt(leftover)} € non investiti" if leftover > 0
                else f"servono {fmt(-leftover)} € oltre il budget")
        warn.append(f"nominale arrotondato al lotto di {fmt(lot, 0)} "
                    f"({fmt(nom, 0)} nominali): {what}.")

    gain_taxable = max(0.0, nom - (nom * clean / 100.0 + commission))
    gain_tax = tax * gain_taxable
    net_coupon = nom * cpn_per_stacco / 100.0 * (1 - tax)
    capital_net = nom - gain_tax

    # Flussi (per IRR) ----------------------------------------------------
    dirty_gross = clean + accrued
    gross_flows = [(settle, -dirty_gross)] + \
        [(d, cpn_per_stacco) for d in cdates] + [(mat, 100.0)]
    net_flows = [(settle, -cash_out)] + \
        [(d, net_coupon) for d in cdates] + [(mat, capital_net)]

    # Bollo stimato: per ogni anno solare, quota pro-rata sul controvalore
    stamps = []
    if stamp > 0:
        total_days = (mat - settle).days
        for y in range(settle.year, mat.year + 1):
            start = max(settle, date(y, 1, 1))
            end = min(mat, date(y, 12, 31))
            if end <= start:
                continue
            frac_year = (end - start).days / 365.0
            t = (end - settle).days / total_days
            px = clean + (100.0 - clean) * t
            stamps.append((end, stamp * nom * px / 100.0 * frac_year))
    net_flows_stamp = net_flows + [(d, -a) for d, a in stamps]

    events = []  # (date, kind, amount, label)
    for d in cdates:
        events.append((d, "cedola", net_coupon, bond["name"]))
    events.append((mat, "capitale", capital_net, bond["name"]))
    for d, a in stamps:
        events.append((d, "bollo", -a, bond["name"]))

    return {
        "bond": bond, "isin": isin, "maturity": mat, "freq": freq, "lot": lot,
        "nom": nom, "accrued": accrued, "cash_out": cash_out, "leftover": leftover,
        "gross": irr(gross_flows, settle), "net": irr(net_flows, settle),
        "net_stamp": irr(net_flows_stamp, settle),
        "net_coupon": net_coupon, "gain_tax": gain_tax, "capital_net": capital_net,
        "stamps": stamps, "events": events, "net_flows": net_flows,
        "net_flows_stamp": net_flows_stamp, "warn": warn, "cdates": cdates,
        "commission": commission,
    }


# ---------------------------------------------------------------- report

def fmt(x, nd=2):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x):
    return "n/d" if x != x else f"{fmt(x * 100)}%"


def build_report(pf, settle):
    tax = float(pf.get("tax", DEFAULT_TAX))
    stamp = float(pf.get("stamp_duty", DEFAULT_STAMP))
    bonds = [analyze(b, settle, tax, stamp) for b in pf["bonds"]]
    last = max(b["maturity"] for b in bonds)
    L = []
    add = L.append

    add("# Portafoglio titoli di Stato — report")
    add(f"\nValuta (settlement): {settle.isoformat()} · Ultima scadenza: "
        f"{last.isoformat()} · Tassa {fmt(tax * 100, 1)}% · Bollo "
        f"{fmt(stamp * 100)}%/anno" + (" (stima)" if stamp else " (escluso)"))

    add("\n## Titoli\n")
    add("| Titolo | ISIN | Prezzo secco | Stato | Cedole/anno | Nominale | Rateo/100 "
        "| Esborso | YTM lordo | Netto | Netto dopo bollo | Cedola netta/stacco | Scadenza |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for b in bonds:
        bd = b["bond"]
        status = "✓ verificato" if bd.get("price_status") == "verified" else "~ stima"
        add(f"| {bd['name']} | {b['isin']} | {fmt(bd['price'])} | {status} | {b['freq']} "
            f"| {fmt(b['nom'], 0)} € | {fmt(b['accrued'], 4)} | {fmt(b['cash_out'])} € "
            f"| {pct(b['gross'])} | {pct(b['net'])} | {pct(b['net_stamp'])} "
            f"| {fmt(b['net_coupon'])} € | {b['maturity'].isoformat()} |")

    notes = [(b["bond"]["name"], w) for b in bonds for w in b["warn"]]
    if notes:
        add("\n**Avvisi**\n")
        for name, w in notes:
            add(f"- {name}: {w}")

    # ---- mappa mese per mese
    per_month = {}
    for b in bonds:
        for d, kind, amount, label in b["events"]:
            per_month.setdefault((d.year, d.month), []).append((kind, amount, label))

    months = []
    y, m = settle.year, settle.month
    while (y, m) <= (last.year, last.month):
        months.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1

    add("\n## Mappa mese per mese (importi netti)\n")
    add("Cedole nette di ritenuta; capitale = rimborso a 100 meno il 12,5% sul "
        "guadagno; bollo = stima pro-rata addebitata a fine anno.")
    year_tot = {}
    cur = None
    for (y, m) in months:
        if y != cur:
            if cur is not None:
                c, k, s = year_tot[cur]
                add(f"| **Totale {cur}** | **{fmt(c)} €** | **{fmt(k, 0)} €** | **{fmt(s)} €** | |")
            cur = y
            year_tot[y] = [0.0, 0.0, 0.0]
            add(f"\n**{y}**\n")
            add("| Mese | Cedole | Capitale | Bollo | Di chi |")
            add("| --- | --- | --- | --- | --- |")
        evs = per_month.get((y, m), [])
        c = sum(a for k, a, _ in evs if k == "cedola")
        k_ = sum(a for k, a, _ in evs if k == "capitale")
        s = sum(a for k, a, _ in evs if k == "bollo")
        year_tot[y][0] += c
        year_tot[y][1] += k_
        year_tot[y][2] += s
        who = []
        for kind, a, label in evs:
            if kind == "capitale":
                who.append(f"RIMBORSO {label}")
            elif kind == "cedola":
                who.append(f"cedola {label}")
        add(f"| {month_label(y, m)} | {fmt(c) if c else '–'} "
            f"| {('**+' + fmt(k_, 0) + ' €**') if k_ else '–'} "
            f"| {fmt(s) if s else '–'} | {'; '.join(who) or '–'} |")
    if cur is not None:
        c, k, s = year_tot[cur]
        add(f"| **Totale {cur}** | **{fmt(c)} €** | **{fmt(k, 0)} €** | **{fmt(s)} €** | |")

    # ---- quando recuperi i soldi
    invested_cash = sum(b["cash_out"] for b in bonds)
    add("\n## Quando recuperi i soldi\n")
    add("| Data | Capitale netto | Titolo | Cumulato | % dell'esborso |")
    add("| --- | --- | --- | --- | --- |")
    cum = 0.0
    for b in sorted(bonds, key=lambda x: x["maturity"]):
        cum += b["capital_net"]
        add(f"| {b['maturity'].isoformat()} | {fmt(b['capital_net'], 0)} € "
            f"| {b['bond']['name']} | {fmt(cum, 0)} € | {fmt(cum / invested_cash * 100, 0)}% |")

    # ---- conto finale
    requested = sum(b["cash_out"] + b["leftover"] for b in bonds)
    leftover = sum(b["leftover"] for b in bonds)
    coupons = sum(c for c, _, _ in year_tot.values())
    capital = sum(b["capital_net"] for b in bonds)
    gain_tax = sum(b["gain_tax"] for b in bonds)
    stamps = -sum(s for _, _, s in year_tot.values())
    commissions = sum(b["commission"] for b in bonds)
    profit = coupons + capital - invested_cash
    all_net = [f for b in bonds for f in b["net_flows"]]
    all_net_s = [f for b in bonds for f in b["net_flows_stamp"]]

    add("\n## Il conto finale\n")
    add("| Voce | Importo |")
    add("| --- | --- |")
    add(f"| Budget indicato | {fmt(requested, 0)} € |")
    add(f"| Esborso effettivo (secco + rateo netto + commissioni) | −{fmt(invested_cash)} € |")
    if abs(leftover) > 0.005:
        lab = ("Liquidità non investita" if leftover > 0 else "Sforamento del budget")
        add(f"| {lab} (arrotondamento ai lotti) | {fmt(abs(leftover))} € |")
    if commissions:
        add(f"| di cui commissioni | {fmt(commissions)} € |")
    add(f"| Cedole nette totali | +{fmt(coupons)} € |")
    add(f"| Capitale rimborsato (netto tassa sul guadagno) | +{fmt(capital)} € |")
    add(f"| di cui tassa 12,5% sul guadagno a scadenza | −{fmt(gain_tax)} € |")
    add(f"| **Guadagno netto (prima del bollo)** | **+{fmt(profit)} €** |")
    if stamp:
        add(f"| Bollo stimato | −{fmt(stamps)} € |")
        add(f"| **Guadagno netto dopo bollo** | **+{fmt(profit - stamps)} €** |")

    add(f"\nRendimento netto del portafoglio (IRR): **{pct(irr(all_net, settle))}**"
        + (f" · dopo bollo: **{pct(irr(all_net_s, settle))}**" if stamp else ""))
    w_avg = sum(b["cash_out"] * b["net"] for b in bonds) / invested_cash
    add(f"\nNetto medio ponderato per esborso: {pct(w_avg)}")

    # ---- copertura mensile per anno pieno
    full_years = [y for y in sorted(year_tot) if settle.year < y < last.year]
    if full_years:
        add("\n## Copertura cedole (anni interi)\n")
        add("| Anno | Mesi con cedola | Cedole nette anno |")
        add("| --- | --- | --- |")
        for y in full_years:
            mm = sorted({mo for (yy, mo), evs in per_month.items() if yy == y
                         and any(k == "cedola" for k, _, _ in evs)})
            add(f"| {y} | {len(mm)}/12 ({', '.join(NOMI_MESI[x - 1] for x in mm)}) "
                f"| {fmt(year_tot[y][0])} € |")

    return "\n".join(L)


def resolve_settle(pf, override):
    if override:
        return date.fromisoformat(override)
    if "settle" in pf:
        return date.fromisoformat(pf["settle"])
    if "trade" in pf:
        return add_business_days(date.fromisoformat(pf["trade"]), 2)
    raise ValueError("serve 'settle' o 'trade' nel JSON (o --settle)")


def main():
    ap = argparse.ArgumentParser(description="Calcola portafogli di bond sovrani")
    ap.add_argument("portafoglio", help="file JSON del portafoglio")
    ap.add_argument("--settle", help="data valuta YYYY-MM-DD (override del JSON)")
    ap.add_argument("--out", help="scrivi il report anche in questo file")
    args = ap.parse_args()

    with open(args.portafoglio, encoding="utf-8") as f:
        pf = json.load(f)
    settle = resolve_settle(pf, args.settle)

    report = build_report(pf, settle)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")


if __name__ == "__main__":
    main()
