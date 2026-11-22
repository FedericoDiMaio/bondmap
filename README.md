# bondmap

> ⚠️ **Non è consulenza finanziaria.** Strumento di calcolo personale: verifica
> sempre prezzi e condizioni col tuo broker; le decisioni sono tue.

Skill (Claude Code / OpenCode) per costruire e rianalizzare portafogli di **titoli di Stato euro-area**
(BTP / OAT / bonos spagnoli): trovare i titoli sotto la pari, calcolare il rendimento
netto reale (12,5% su cedole e guadagno a scadenza, rateo, bollo), fare il **mapping mese per mese** delle cedole e dei rimborsi,
verificare "quando recupero i soldi", e produrre la checklist ordini per il broker.

## Struttura

```
bondmap/
├── SKILL.md                 # la skill: workflow in 4 fasi + regole di correttezza
├── scripts/
│   └── bondcalc.py          # rendimenti netti, mappa mensile (Python, zero dipendenze)
├── references/
│   ├── datasources.md       # dove prendere liste e prezzi (e quali strade sono morte)
│   ├── methodology.md       # cedola vs netto, frequenza cedole, rateo, tasse, bollo
│   ├── example.md           # caso di esempio completo: 5×6k con mappa mese per mese
│   └── example_portfolio.json  # JSON del caso di esempio (numeri di controllo)
├── example_report.md        # output atteso di bondcalc.py sul caso di esempio
├── .claude-plugin/
│   └── plugin.json
├── LICENSE                  # MIT
└── README.md
```

## Installazione

### Nell'app Claude (web, desktop)

1. Scarica **`bondmap.zip`** dalla pagina
   [Releases](https://github.com/FedericoDiMaio/bondmap/releases) (non usare
   "Code → Download ZIP": crea una cartella `bondmap-main` che Claude non
   riconosce).
2. Impostazioni → Funzionalità: attiva l'esecuzione del codice / creazione file.
3. Barra laterale → **Plugin** → carica `bondmap.zip`.
4. In chat scrivi `/bondmap` seguito dalla richiesta, oppure chiedi in
   linguaggio naturale ("fammi un portafoglio di BTP sotto la pari").

### In Claude Code

```bash
git clone https://github.com/FedericoDiMaio/bondmap ~/.claude/skills/bondmap
```

### In OpenCode

```bash
git clone https://github.com/FedericoDiMaio/bondmap ~/.agents/skills/bondmap
```

## Uso tipico

```
"training dei BTP: 30k, tutto indietro entro fine 2030, mix Italia-Francia, tutto sotto la pari"
"aggiungi 6k su un OAT 2028 e rifammi la mappa"
"quanti bonos spagnoli 2027-2028 sono sotto la pari?"
"quando recupero i soldi?"
```

La skill lavora in 4 fasi: (0) vincoli → (1) dati reali → (2) calcolo con
`bondcalc.py` → (3) mappa + decisione → (4) checklist ordini.

## Garanzia dei numeri

- Ogni numero del portafoglio deve essere **verificato** (prezzo reale di oggi) o
  **esplicitamente marcato come stima**. Il skill impone sempre la distinzione.
- Il netto è l'IRR dei flussi netti reali: esborso (corso secco + rateo netto +
  commissioni) → cedole nette 12,5% → rimborso a 100 meno il 12,5% sul guadagno.
  Viene mostrato anche il netto dopo bollo (0,20%/anno).
- Frequenza cedole per Paese: BTP semestrali, OAT e bonos annuali.
- Nominali arrotondati al lotto minimo, valuta T+2 lavorativi.
- Test di regressione: `python3 scripts/bondcalc.py references/example_portfolio.json`
  deve dare IRR netto **3,34%** (output completo in `example_report.md`).
