# Methodology — cedola, netto, sotto la pari, tasse

Spiegazioni pronte per l'utente (in italiano, senza gergo) e le regole che
stanno dietro `bondcalc.py`. Se l'utente chiede "dove leggi che il netto è X%",
la risposta onesta è: "non si legge da nessuna parte, si calcola: ecco come".

## Cedola vs netto

- **Cedola** (es. 2,70%): l'interesse fisso stampato sul titolo, sul nominale
  (il 100). Dato di fabbrica, non cambia mai. Risponde a "quanto paga in busta".
- **Netto** (es. 3,53%): il rendimento reale comprando oggi al prezzo di
  mercato e tenendo fino al rimborso a 100, dopo le tasse. Risponde a
  "quanto rendi davvero".
- Il netto è il numero che si usa per confrontare titoli e decidere.

## Frequenza delle cedole (dipende dal Paese)

| Emittente | Cedole | Date |
| --- | --- | --- |
| BTP (Italia) | **semestrali** | giorno di scadenza e 6 mesi prima (es. 01/03 e 01/09) |
| OAT (Francia) | **annuali** | giorno e mese della scadenza (di solito il 25; alcune emissioni recenti il 24) |
| Bonos / Obligaciones (Spagna) | **annuali** | giorno e mese della scadenza (es. 30/04, 31/10, 31/01) |
| Bund, OLO, DSL, RAGB… | annuali | data anniversario della scadenza |

Regola: **l'ultima cedola si paga sempre alla scadenza, insieme al capitale**.
Le date di stacco si ricavano dalla scadenza; lo script lo fa da solo
(`frequency` di default: 2 per ISIN `IT`, 1 per tutti gli altri).
Eccezione: le nuove emissioni possono avere una prima cedola "corta" o
"lunga" — se compri prima del primo stacco, verifica sul prospetto.

## Le componenti del netto

Per ogni 100 di nominale comprato al corso secco `P`:

| Componente | Calcolo | Tassazione |
| --- | --- | --- |
| Cedole | `cedola% / anno` su 100 | **12,5%** (ritenuta alla fonte) |
| Guadagno a scadenza | `100 − P` se P < 100 | **12,5%** (reddito diverso: 26% sul 48,08% della base) |
| Perdita a scadenza | `P − 100` se P > 100 | genera una minusvalenza (credito), usabile solo se hai plusvalenze future |
| Bollo | 0,20% annuo sul controvalore del dossier | si paga anche sui titoli di Stato |

Il guadagno di rimborso **non è esente**: è tassato al 12,5% come le cedole.
Il vantaggio del sotto la pari è un altro: quel guadagno è un *reddito
diverso*, quindi **compensabile con minusvalenze pregresse** (zainetto
fiscale). Se l'utente ha minusvalenze, il netto reale sui titoli sotto la
pari sale: lo script è prudente e non lo assume.

Lo script calcola il netto come **IRR dei flussi netti reali**:
esborso effettivo (secco + rateo netto + commissioni) → cedole nette →
rimborso 100 meno il 12,5% sul guadagno. Il "netto dopo bollo" sottrae
anche lo 0,20% annuo stimato.

Formula rapida per il controllo a mano (±10 bp):

```
lordo ≈ cedola/P + (100 − P) / (P × anni)
netto ≈ lordo × 0,875
dopo bollo ≈ netto − 0,20%
```

Esempio: OAT 2,70% feb 2031 a 94,89 con 4,26 anni → lordo ≈ 2,85% + 1,26% =
4,1% (lo script: 4,02%) → netto ≈ 3,55% (lo script: 3,53%).

## Rateo (accrued interest)

Il prezzo quotato (MOT, Euronext) è il **corso secco**, senza interessi
maturati. Comprando tra due stacchi paghi al venditore anche il rateo
(per i titoli italiani a 12,5%, al netto della ritenuta); al primo stacco
incassi la cedola intera.

- Il rateo **è un esborso vero in più** il giorno dell'acquisto: per l'OAT
  feb 2031 comprata il 23/11/2026 sono ~2 punti su 100 (9 mesi di cedola).
- Ignorarlo (pagare 94,89 e incassare tutta la prima cedola) **gonfia il
  rendimento** di decine di bp sui titoli a cedola annuale.
- Rateo ACT/ACT: `cedola_per_stacco × giorni_dall'ultimo_stacco / giorni_del_periodo`.

## Valuta (settlement) e lotti

- MOT e Euronext regolano a **T+2 lavorativi** (calendario TARGET2): un
  ordine di giovedì 19/11 ha valuta lunedì 23/11. Il rateo si conta fino
  alla valuta. Nel JSON usa `"trade"` e lo script calcola la valuta.
- Taglio minimo: **1.000 € nominali** per BTP su MOT e bonos; OAT taglio
  1 € (ma il broker può imporre lotti più grandi → campo `lot`). Con 6.000 €
  di budget su un BTP a 97 compri 6.000 nominali e avanzano ~150 €.

## Perché il prezzo scende sotto la pari

Il bond è stato emesso quando i tassi erano `c` (la sua cedola). Se i tassi
di mercato salgono a `y > c`, il prezzo si abbassa finché il rendimento
totale (cedole + rialzo) non torna ~`y`. Il mercato fa questo aggiustamento
da solo.

| Prezzo | Netto vs cedola netta | Esempio (versione corretta) |
| --- | --- | --- |
| P < 100 | netto **>** cedola × 0,875 | OAT 2,70% a 94,89 → 3,53% |
| P ≈ 100 | netto ≈ cedola × 0,875 | BTP 3,50% a 99,47 → 3,24% |
| P > 100 | netto **<** cedola × 0,875 | BTP 4% nov 2030 a 100,70 → 3,34% |

(valuta 23/11/2026; il BTP 4% scade il **15/11/2030**, non il 1°.)

## Tassazione (residente italiano, regime amministrato)

- Cedole e guadagno a scadenza: **12,5%** su BTP e su titoli di Stato
  esteri di Paesi della white list (OAT, bonos inclusi). Chiedere alla banca
  conferma che non applichi ritenute estere.
- Vendita prima della scadenza con plusvalenza: **12,5%** effettivo
  (non 26%: per i titoli di Stato la base è il 48,08%).
- Minusvalenze (titolo comprato sopra la pari): credito d'imposta usabile
  entro il 4° anno successivo contro plusvalenze, ma una minusvalenza da
  titolo di Stato vale solo il 48,08% contro plusvalenze tassate al 26%.
- Bollo 0,20% annuo sul controvalore, di solito addebitato trimestralmente.
  Gli 0,20% pesano ~20 bp l'anno sul rendimento: vanno mostrati.

## Copertura mensile delle cedole

- Ogni **BTP** paga in 2 mesi l'anno, coppie fisse:
  `gen↔lug   feb↔ago   mar↔set   apr↔ott   mag↔nov   giu↔dic`
- Ogni **OAT o bono** paga in **1 solo mese** l'anno.
- Copertura massima: 2 mesi per BTP + 1 mese per titolo estero (se le
  coppie/mesi non si sovrappongono). Per 12 mesi servono 6 BTP con coppie
  diverse, oppure p.es. 4 BTP + 4 esteri ben scelti.
- Il caso 5×6k (3 BTP + 2 OAT) copre **7 mesi**, non 10.

## Stima dei prezzi mancanti (quando il market data non c'è)

1. Costruire la curva YTM lorda dai prezzi **verificati** della stessa area
   (calcolati con lo script, rateo incluso).
2. Interpolare linearmente lo YTM alla scadenza desiderata (extrapolare poco
   fuori range, con cautela sul corto).
3. Scontare i cash flow del bond a quel tasso → prezzo tel quel; togliere il
   rateo → corso secco di stima.
4. Marcare tutto con `~` e "da confermare col broker".

## Aste del Tesoro vs broker (secondario)

| | Asta (primario) | Broker (secondario) |
| --- | --- | --- |
| Prezzo | prezzo di aggiudicazione = mercato; nelle **riaperture** può essere ben sotto 100 | prezzo di mercato |
| Commissioni | massime fissate dal MEF (spesso zero sui BTP medio-lunghi, piccole sui BOT) | chiedere l'all-in |
| Menu | solo i titoli del calendario del mese (nuove emissioni e riaperture, anche off-the-run) | qualsiasi ISIN, + OAT e bonos |
| Quando | due finestre al mese (metà e fine mese), date nel calendario annuale MEF | sempre |
| Protezioni | il retail compra al prezzo d'asta (ordine non competitivo) | ordine a limite |

Per un ISIN preciso non in asta questo mese, e per tutti gli OAT/bonos,
l'unica strada è il secondario. Se il titolo voluto è in riapertura, l'asta
può dare lo stesso sconto del mercato senza commissioni di negoziazione.

## Checklist di onestà (usare ogni volta)

- [ ] Ogni prezzo è marcato verificato ✓ o stima ~
- [ ] I netti vengono da `bondcalc.py`, non a mano
- [ ] Frequenza cedole corretta per Paese (BTP 2, OAT/bonos 1)
- [ ] Rateo e valuta T+2 inclusi; nominale arrotondato al lotto
- [ ] Tassa 12,5% sul guadagno a scadenza inclusa; bollo mostrato
- [ ] I mesi vuoti della cedola sono dichiarati
- [ ] Se un target (netto, cedola/anno) non è raggiungibile col vincolo, il
      tetto matematico è mostrato
- [ ] La concentrazione per Paese/scadenza è dichiarata
- [ ] Il "quando recuperi i soldi" è una tabella con date e %
