# Example — caso di esempio (novembre 2026)

Caso completo di riferimento. Serve come: (a) formato atteso delle uscite,
(b) numeri di controllo per `bondcalc.py` (test di regressione).

> **Versione 1.1 — numeri ricalcolati.** La versione 1.0 dello script
> trattava le OAT come semestrali, ignorava il rateo, considerava esente il
> guadagno a scadenza e non arrotondava ai lotti: i netti erano gonfiati di
> 35-45 bp (OAT feb 2031: 3,87% → **3,53%**). I numeri qui sotto sono
> quelli corretti.

## Profilo e vincoli (di esempio)

- Investitore retail italiano, broker (banca), regime amministrato →
  12,5% su cedole **e** sul guadagno a scadenza; bollo 0,20%/anno.
- **Capitale**: 30.000 €, acquisti a novembre 2026.
- **Vincolo di uscita**: tutto il capitale indietro entro inizio 2031.
- **Sotto la pari**: obbligatorio (i titoli sopra 100 sono scartati: il
  BTP 4% 15/11/2030 a 100,70 è escluso per questo).
- **Target**: ~3,5% netto; ~€1.000/anno di cedola.
- **Mix**: Italia + Francia (Spagna su richiesta).
- **Prodotto atteso**: sempre la mappa mese per mese + "quando recupero i soldi".

## Mercato di riferimento (19/11/2026)

- Inflazione Italia 5,5%, Eurozona 4%; Fed in ciclo di rialzi.
- BTP 10y 4,40%; BTP-Bund spread 104-107 bp; Bund 10y ~3,33%.
- Spread FR 10y ~1,5 pp (massimo in UE); ES ~0,7 pp.

## Prezzi verificati (chiusura Euronext / MOT 19/11/2026, corsi secchi)

| ISIN | Titolo | Scadenza | Cedole | Prezzo |
| --- | --- | --- | --- | --- |
| FR001400Z2L7 | OAT 2,70% feb 2031 | 25/02/2031 | annuale | 94,89 |
| FR001400XLW2 | OAT 2,40% set 2028 | 24/09/2028 | annuale | 97,95 |
| FR001400NBC6 | OAT 2,50% set 2027 | 24/09/2027 ? | annuale | 99,52 |
| FR001400PM68 | OAT 2,75% feb 2030 | 25/02/2030 ? | annuale | 96,39 |
| FR0014018OI0 | OAT 3,25% feb 2032 | 25/02/2032 ? | annuale | 95,20 |
| FR001400QMF9 | OAT 3,00% nov 2034 | 25/11/2034 ? | annuale | 89,18 |
| IT0005637399 | BTP 2,95% lug 2030 | 01/07/2030 | semestrale | 97,31 |
| IT0005024234 | BTP 3,50% mar 2030 | 01/03/2030 | semestrale | 99,47 |
| IT0005654642 | BTP 2,70% ott 2030 | 01/10/2030 | semestrale | 96,13 |
| IT0005561888 | BTP 4,00% nov 2030 | **15/11/2030** | semestrale | 100,70 (sopra pari, scartato) |

Le date con `?` sono dedotte dal nome del titolo (giorno tipico AFT): da
riconfermare sulla scheda AFT prima di usarle. Da riconfermare anche la
scadenza esatta del BTP 2,95% lug 2030.

## Portafoglio scelto: 5 × 6.000 € (ordini 19/11/2026, valuta 23/11/2026)

```
6.000 → OAT 2,70% feb 2031
6.000 → OAT 2,40% set 2028
6.000 → BTP 2,95% lug 2030
6.000 → BTP 3,50% mar 2030
6.000 → BTP 2,70% ott 2030
```

### Output di `bondcalc.py` (file: `example_portfolio.json`)

Numeri di controllo (se questi cambiano, lo script è stato rotto):

| Titolo | Nominale | Rateo/100 | Esborso | Lordo | Netto | Dopo bollo | Cedola netta/stacco |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OAT 2,70% feb 2031 | 6.208 | 2,0047 | 5.999,66 € | 4,02% | 3,53% | 3,33% | 146,66 € (feb) |
| OAT 2,40% set 2028 | 6.104 | 0,3945 | 5.999,94 € | 3,56% | 3,12% | 2,92% | 128,18 € (set) |
| BTP 2,95% lug 2030 | 6.000 | 1,1624 | 5.899,62 € | 3,79% | 3,32% | 3,11% | 77,44 € |
| BTP 3,50% mar 2030 | 6.000 | 0,8025 | 6.010,33 € | 3,71% | 3,24% | 3,04% | 91,88 € |
| BTP 2,70% ott 2030 | 6.000 | 0,3931 | 5.788,44 € | 3,82% | 3,35% | 3,14% | 70,88 € |

- Esborso totale 29.698,00 € (302 € restano liquidi per i lotti BTP da 1.000).
- **Rendimento netto del portafoglio (IRR): 3,34%** · dopo bollo **3,14%**.
- Cedole 2027: 77,44 (gen) · 146,66 (feb) · 91,88 (mar) · 70,88 (apr) ·
  77,44 (lug) · 220,06 (set) · 70,88 (ott) → **755 €/anno, 7 mesi su 12**
  (2027-28); 2029: 627 €; 2030: 535 €.
- Rimborsi (netti della tassa sul guadagno): **24/09/2028 6.088 €** →
  01/03/2030 5.996 → 01/07/2030 5.980 → 01/10/2030 5.971 →
  **25/02/2031 6.168 €**.
- Totale: cedole nette +2.819 €, capitale +30.204 € (tassa sul guadagno
  −108 €), **guadagno +3.325 €**, bollo stimato −201 € → **+3.124 € netti**.

### Lezione di coerenza

Il target "~3,5% netto" **non è raggiungibile** con questi titoli e questo
vincolo: il portafoglio fa 3,34% (3,14% dopo bollo). Il titolo migliore
(OAT feb 2031) arriva a 3,53%. Va detto all'utente, non nascosto.

### Confronto 4 quote vs 5 quote

| | 4 quote (12k OAT 2031) | 5 quote (+6k OAT 2028) |
| --- | --- | --- |
| Netto IRR / dopo bollo | 3,40% / 3,20% | 3,34% / 3,14% |
| Cedola 2027-28 | ~774 €/anno | ~755 €/anno |
| Mesi con cedola | 7/12 | 7/12 |
| Primi soldi indietro | mar 2030 | **set 2028** |
| Guadagno netto dopo bollo | ~+3.652 € | ~+3.124 € (+ reinvestimento dei 6k dal 2028) |
| Concentrazione | 40% in un titolo | max 20% per titolo |

## Breve termine (2027-2028)

- FR: OAT 2,50% set 2027 (99,52 ✓, ~10 mesi): netto 2,70%, +135 € su 6k
  (+125 € dopo bollo). OAT 2,40% set 2028 (97,95 ✓, ~22 mesi): netto
  3,12%, +345 € su 6k (+323 € dopo bollo).
- ES: ISIN ufficiali da tesoro.es (2027: ES0000012J15 0%, ES00000128P8 1,50%,
  ES0000012M77 2,50%, ES0000012G26 0,80%, ES0000012A89 1,45%; 2028:
  ES0000012I08 0%, ES0000012B39 1,40%, ES0000012O59 2,40%, ES0000012B88 1,40%).
  Cedole **annuali**. Prezzi solo indicativi (~99,4 / ~99,7 / ~98,9 /
  ~96,8 / ~97,4) — da broker.
- I cedoloni spagnoli (5,15% 2028 ES00000124C5 ~103; 6,00% 2029 ES0000011868
  ~106,6) sono sopra la pari → fuori dalle regole del profilo.
- Conclusione corretta: il corto rende **meno** del core (2,7-3,1% netto
  contro 3,2-3,5%) ma restituisce il capitale prima.
