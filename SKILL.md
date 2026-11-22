---
name: bondmap
description: >-
  Costruisce e rianalizza portafogli di titoli di Stato euro-area
  (BTP italiani, OAT francesi, bonos spagnoli). Trova i titoli sotto la pari,
  calcola il rendimento netto reale (12,5% su cedole e guadagno a scadenza,
  rateo, bollo), produce
  il mapping mese per mese di cedole e rimborsi, verifica "quando recupero i
  soldi", confronta i Paesi e prepara la checklist ordini per il broker.
  Usa questa skill quando l'utente vuole fare "training dei BTP", costruire o
  rifare un portafoglio obbligazionario sovrano, cercare BTP/OAT/bonos sotto
  la pari o a breve scadenza, chiedere rendimenti netti di obbligazioni di
  Stato, vedere la mappa mese per mese delle cedole, capire quando torna il
  capitale, fare un mix Italia/Francia/Spagna, confrontare aste del Tesoro e
  broker, o preparare gli ordini da mandare alla banca. Anche frasi come
  "quanto rende netto questo BTP", "aggiungi 6k su un OAT e rifammi la
  mappa", "c'è altro sotto i 100?", "fammi il prospetto dei guadagni".
argument-hint: "[importo] [ultimo anno di rimborso accettato] [mix IT/FR/ES] [tutto sotto la pari?]"
---

# bondmap — portafogli di titoli di Stato

Questo skill guida la costruzione (o la rianalisi) di un portafoglio di
obbligazioni sovrane euro-area con numeri reali e una mappa del flusso di
cassa mese per mese, per un investitore residente in Italia che compra sul
secondario tramite broker e tiene i titoli fino a scadenza.

`CLAUDE_SKILL_DIR` (o l'equivalente nel tuo harness) = la cartella di questa
skill, dove vivono `scripts/` e `references/`.

## Principi non negoziabili

1. **Ogni numero è verificato o è una stima marcata come tale.** Un prezzo
   "verificato" è quello letto oggi da una fonte (MOT via btpitalia.com,
   chiusura Euronext via Yahoo, scheda del broker). Una "stima" è derivata
   dalla curva o da dati vecchi: si marca sempre con `~` e "da confermare
   col broker". Mai presentare una stima come dato di mercato.
2. **Il netto si calcola, non si legge.** Le fonti non pubblicano il
   rendimento netto: lo calcoli con `scripts/bondcalc.py` (IRR dei flussi
   netti reali: esborso con rateo → cedole nette → rimborso meno il 12,5%
   sul guadagno; e la versione dopo bollo 0,20%). Se ti chiedono "dove
   leggi che il netto è X%", la risposta è: "l'ho calcolato io, ecco il
   calcolo".
3. **Sotto la pari = requisito, non opzione** (salvo che l'utente dica il
   contrario): il rialzo a 100 fa salire il rendimento sopra la cedola. È
   tassato al 12,5% come le cedole, ma come reddito diverso è compensabile
   con minusvalenze pregresse; sopra la pari si incassa invece una perdita
   certa a scadenza.
4. **Il mapping è il prodotto.** Ogni proposta di portafoglio include la
   mappa mese per mese (cedole nette + rimborsi) e la tabella
   "quando recuperi i soldi". Senza mappa non si propone.
5. **Onestà sui vincoli.** Se il target (es. 3,5% netto) o la cedola
   desiderata (es. 1.000 €/anno) non sono raggiungibili col vincolo di
   scadenza, dirlo esplicitamente e mostrare il tetto matematico.

## Workflow in 4 fasi

### Fase 0 — Vincoli (chiedi prima, non dopo)

Raccogli questi parametri (non richiederli di nuovo se l'utente li ha già
dati nella conversazione):

| Parametro | Domanda | Esempio |
| --- | --- | --- |
| Capitale | Quanto investi, e in che tranche? | 30.000 € subito + 15.000 € tra sei mesi |
| Uscita | Qual è l'ultimo anno in cui il capitale torna? | entro 4 anni |
| Netta target | Che rendimento minimo accetti? | ~3,5% |
| Cedola target | Quanto cash vuoi all'anno? | ~1.000 € |
| Mix | Quali Paesi? | Italia + Francia (+ Spagna) |
| Sotto la pari | Escludi i titoli sopra 100? | Sì |
| Broker | Dove ordini? | banca/broker in regime amministrato → 12,5% |
| Periodicità cedole | Quanti mesi coperti vuoi? | 12 mesi = 6 BTP; ogni OAT/bono aggiunge 1 mese |
| Minusvalenze | Hai minusvalenze pregresse da compensare? | (se sì, il sotto la pari rende di più) |

Regola dei mesi: ogni **BTP** paga in **2 mesi** l'anno (coppie fisse:
gen–lug, feb–ago, mar–set, apr–ott, mag–nov, giu–dic); ogni **OAT o
bono** paga in **1 solo mese** (cedola annuale, alla data anniversario
della scadenza). Copertura massima = 2 × n.BTP + n.esteri, se non si
sovrappongono. Esempio: 3 BTP + 2 OAT = al più 8 mesi (il caso di
`references/example.md` ne copre 7). Per 12 mesi servono 6 BTP su coppie diverse. Dimostrarlo prima
fa capire i compromessi.

### Fase 1 — Dati reali

Leggi `references/datasources.md` e prendi:

1. **Liste ufficiali** con ISIN, cedola, scadenza (e saldi in circolazione):
   BTP da btpitalia.com, OAT da AFT, bonos da tesoro.es.
2. **Prezzi di oggi**: BTP da btpitalia.com (quotazioni MOT serali);
   OAT dalla chiusura Euronext via Yahoo Finance (procedura esatta nel
   file datasources, inclusa la via in-app perché i siti bloccano curl).
3. **Prezzi del broker** (se c'è la scheda rischio in PDF): può
   differire di qualche decimale da Euronext — usalo come riferimento
   d'esecuzione e ricalcola.

Per ogni ISIN candidato annota: `verificato` / `~ stima`.

### Fase 2 — Calcolo

Scrivi il file di portafoglio JSON e lancia lo script (zero dipendenze,
Python 3.8+):

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/bondcalc.py" portafoglio.json
```

Formato JSON (vedi anche `references/example.md` per il caso completo):

```json
{
  "trade": "2026-11-19",
  "stamp_duty": 0.002,
  "bonds": [
    {"isin": "FR001400Z2L7", "name": "OAT 2,70% feb 2031",
     "coupon": 2.70, "maturity": "2031-02-25", "price": 94.89,
     "invested": 6000, "price_status": "verified"}
  ]
}
```

- `trade` = data ordine (valuta calcolata a T+2 lavorativi TARGET2);
  in alternativa `settle` esplicito.
- `price` = **corso secco** quotato; lo script aggiunge il rateo.
- `maturity` = data esatta (molti BTP scadono il 15, non il 1°).
- Opzionali per titolo: `nominal` (al posto di `invested`), `frequency`
  (default 2 per ISIN IT, 1 per gli altri), `lot` (default 1.000; 1 per
  ISIN FR), `commission` (€). `coupon_months` non serve più: le date
  vengono dalla scadenza (se lo metti, viene solo controllato).
- `stamp_duty: 0` per escludere il bollo.

Lo script restituisce (markdown): per ogni bond nominale arrotondato al
lotto, rateo, esborso, YTM lordo, netto, netto dopo bollo, cedola netta per
stacco; avvisi (sopra la pari, stime, lotti, mesi incoerenti); la mappa
mese per mese con capitale e bollo e i totali per anno; "quando recuperi i
soldi"; il conto finale con IRR del portafoglio; la copertura mesi per anno.

Controlla sempre l'output a mano per un paio di righe (formula rapida in
`references/methodology.md`; che i rimborsi cadano nel mese giusto e che la
copertura mensile sia quella attesa). Se un prezzo è `~ stima`, i suoi
numeri vanno presentati come stime.

### Fase 3 — Mappa e decisione

Presenta all'utente, in questo ordine:

1. **Tabella portafoglio**: importo, titolo, ISIN, prezzo (✓ o ~), netto
   e netto dopo bollo, data rimborso.
2. **Mappa mese per mese** per anno (cedole nette + "R" sui rimborsi) e i
   totali annuali.
3. **Quando recuperi i soldi**: data, importo, % cumulata.
4. **Il conto finale**: investito, cedole nette totali, capitale, guadagno.
5. **I compromessi onesti**: mesi senza cedola, concentrazione per Paese e
   scadenza, eventuale quota sopra la pari, distanza dai target.

Se l'utente confronta due varianti (es. 4 quote vs 5 quote), fai la tabella
faccia a faccia: netto medio, cedola/anno, primi soldi indietro, guadagno
totale, concentrazione. Il guadagno assoluto più basso di una variante va
spiegato (es. capitale indietro prima = meno tempo a lavorare, ma
reinvestibile).

### Fase 4 — Checklist ordini

Quando il portafoglio è approvato, produci:

```
ORDINI DA INVIARE AL BROKER (data, importi, ISIN)
1. <ISIN> — <nome> — <nominale> nominali (~<esborso> € con rateo) — prezzo limite ≤ <prezzo secco> — mercato (MOT / Euronext Paris)
...
Domande da fare alla banca:
- Prezzo all-in (quota + commissione) per ogni ordine
- Per gli OAT: prezzo "fermo" non "indicativo" (mercato meno liquido)
- Conferma del rendimento a scadenza sul ticket di esecuzione
- Nessuna ritenuta estera su OAT/bonos (regime 12,5% white list)
Nota: l'ordine si dà in nominale (lotti); in più si paga il rateo netto,
che torna col primo stacco. Valuta T+2.
```

Ricorda: le **aste del Tesoro** offrono solo i titoli in calendario quel
mese (nuove emissioni e riaperture), al prezzo d'asta che è di mercato —
nelle riaperture anche molto sotto 100 — con commissioni massime fissate
dal MEF. Per ISIN non in asta e per gli OAT/bonos l'unica strada è il
secondario via broker.

## Errori da non commettere

- **Calcolare il netto con formule approssimate** e presentarlo come
  definitivo: usa sempre `bondcalc.py`; la formula rapida serve solo da
  controllo.
- **Trattare OAT e bonos come semestrali**: pagano una volta l'anno, alla
  data anniversario della scadenza (OAT 2,40% 24/09/2028 → ogni 24/09,
  ultima cedola insieme al rimborso).
- **Ignorare il rateo**: il prezzo quotato è secco; comprando a novembre un
  titolo che stacca a febbraio paghi ~9 mesi di cedola in più. Senza rateo
  il netto risulta gonfiato di 20-40 bp.
- **Dire che il rialzo a 100 è esente**: è tassato al 12,5%.
- **Dimenticare il bollo** (0,20%/anno, ~20 bp di rendimento) e i lotti
  minimi (1.000 nominali per i BTP).
- **Assumere che i BTP scadano il 1° del mese**: molti scadono il 15.
- **Promettere la cedola mensile in tutti e 12 i mesi** con pochi titoli:
  ogni bond copre 2 mesi, dimostrarlo prima evita delusioni.
- **Fidarsi dei prezzi dai riassunti AI** (AI Overviews, chatbot): gli ISIN
  vanno verificati contro la fonte ufficiale (btpitalia/AFT/tesoro.es) e i
  prezzi contro un market data reale; se non si trova, si marca "stima".
- **Usare una tassazione diversa per i titoli esteri**: per un residente
  italiano OAT e bonos (Paesi white list) hanno lo stesso 12,5% del BTP, su
  cedole e guadagno; il bollo si paga su tutto il dossier.

## Risorse

| File | Quando leggerlo |
| --- | --- |
| `references/datasources.md` | Fase 1: dove e come prendere liste e prezzi, siti che bloccano e vie d'accesso |
| `references/methodology.md` | Spiegare all'utente cedola vs netto, frequenza cedole, sotto la pari, rateo, tasse, bollo; formula di controllo |
| `references/example.md` | Caso di esempio completo (5×6k, mappa 2027-2031): formato atteso e numeri di controllo per bondcalc.py |
| `references/example_portfolio.json` | JSON del caso di esempio: `python3 scripts/bondcalc.py references/example_portfolio.json` deve dare IRR netto 3,34% |
| `scripts/bondcalc.py` | Fase 2: eseguilo sempre per i numeri, mai a mano |
