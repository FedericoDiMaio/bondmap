# Datasources — dove prendere liste e prezzi

Ultima verifica: 19/11/2026. L'accessibilità dipende dalla rete da cui si
lavora (proxy aziendali, WAF): ogni voce riporta
ciò che funziona e la via d'accesso. "Via shell" = `curl` dal terminale utente;
"via browser" = browser integrato dell'app (Chromium reale, rete del server
collegato, che può essere diversa da quella della shell).

## 1. BTP italiani — btpitalia.com (VIA SHELL)

La fonte più comoda: lista completa con **ISIN, cedola, scadenza, prezzo MOT**.

- Lista completa: `https://www.btpitalia.com/btp` (HTML, tabella per scadenza;
  i prezzi sono la chiusura MOT della sera, es. "19/11/2026 17:39").
- Breve termine: `https://www.btpitalia.com/btp/breve-termine` (32 titoli 2026-2028).
- Calendario aste: sito MEF / Dipartimento del Tesoro (calendario annuale;
  due finestre al mese, metà e fine mese — non c'è un giorno fisso).
- Le scadenze BTP **non sono tutte il 1° del mese**: molte emissioni scadono
  il 15 (es. BTP 4% IT0005561888 → 15/11/2030), alcune il 30 o in altri
  giorni. Prendere sempre la data esatta dalla lista; le cedole semestrali
  cadono nello stesso giorno, nel mese di scadenza e a −6 mesi.
- Fonte di riscontro per scadenza e cedola: la scheda Borsa Italiana
  `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/<ISIN>.html`.

Estrazione rapida:
```bash
curl -s https://www.btpitalia.com/btp -o btp.html
python3 - <<'EOF'
import re
h = open('btp.html').read()
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S)
for r in rows:
    cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
    if any(c.startswith('IT000') for c in cells):
        print(' | '.join(cells))
EOF
```

## 2. OAT francesi — AFT + Yahoo Euronext (VIA BROWSER)

### Lista ufficiale (ISIN, cedola, scadenza, saldi)
`https://www.aft.gouv.fr/en/encours-detaille-oat`

- **Bloccato da Cloudflare per curl** (403 + challenge). Il browser integrato
  (Chromium) supera il challenge: aprirlo, aspettare il load, poi estrarre le
  tabelle col DOM (34 tabelle, una per anno di scadenza).
- AFT va spesso **in manutenzione** ("SITE EN MAINTENANCE"): se capita, i dati
  della lista li hai già, oppure riprova in giornata.

- **Le OAT pagano una cedola l'anno** ("Annual, paid on 25 <mese> of each
  year" nelle schede AFT per singolo ISIN), nel giorno/mese di scadenza.
  Nel JSON: nessun `coupon_months`, `frequency` 1 è il default per ISIN FR.
- Le schede AFT per ISIN (`aft.gouv.fr/en/node/<id>`) riportano cedola,
  scadenza, base ACT/ACT e storico aste: sono la fonte da citare.

### Prezzi di mercato
Le OAT quotate su **Euronext Paris** sono su Yahoo Finance col suffisso **`.PA`**:
`FR001400Z2L7.PA`, `FR0014018OI0.PA`, ecc.

- **L'API chart di Yahoo non risponde a curl** (429 Too Many Requests).
  Funziona solo con **fetch in pagina** da una tab su `finance.yahoo.com`
  (stessa origine):
  ```js
  // dentro browser.evaluate, su una tab Yahoo:
  const r = await fetch('https://query1.finance.yahoo.com/v8/finance/chart/FR001400Z2L7.PA?range=5d&interval=1d',
                        { credentials: 'include' });
  const m = (await r.json()).chart.result[0].meta;
  // m.regularMarketPrice = chiusura
  ```
- Le OAT **meno liquide** (es. FR0012993103, FR0013516549, FR0000187635) danno
  **404 su Yahoo**: in quel caso il prezzo lo dà solo il broker (market maker)
  → marcarlo `~ stima` o "da broker".
- **Le tab browser chiudono tra una chiamata e l'altra**: prima di ogni
  `evaluate`, `tabs.list()` e riusa l'id; se manca, riapri la tab Yahoo.
- Il search API di Yahoo (`/v1/finance/search?q=`) è debole sui bond: cerca
  per ISIN esatto, non per nome.

## 3. Bonos spagnoli — tesoro.es (VIA SHELL)

La fonte ufficiale spagnola funziona da shell (i siti `.gob.es` del ministero
sono inaccessibili, ma tesoro.es risponde):

- **Lista ufficiale completa** (ISIN, tipo/cedola, scadenza, saldo, a data
  recente): `https://www.tesoro.es/es/deuda-publica/valores-del-tesoro/valores-en-circulacion`
  → tabella `<table id="tablaByo">` in HTML semplice (parse con regex).
- I bonos sovrani hanno prefisso **`ES0000012`** (vecchie emissioni
  `ES00000118xx`); le lettere sono `ES0L`.
- **Bonos e Obligaciones pagano una cedola l'anno**, nel giorno e mese di
  scadenza (es. scadenza 30/04 → cedola ogni 30/04; scadenza 31/01 → ogni
  31/01). Nelle schede di emissione del Banco de España: "Pago intereses:
  Anualmente, el <giorno> de <mese> de cada año". Le nuove emissioni
  possono avere un primo cupón irregolare: verificarlo se si compra prima
  del primo stacco.
- Taglio minimo 1.000 € nominali.
- I bonos NON sono su Yahoo (404 con `.MA` e `.ES`): i prezzi si prendono da
  market data secondario (e vanno marcati `~ stima` se non verificati) oppure
  si chiede al broker la quotazione EUROMOT/AIAF.

## 4. Prezzi del broker (banca)

- La **Scheda Rischio** (PDF) contiene: ultimo prezzo disponibile (fonte della
  banca, può differire di qualche decimale da Euronext), tassa 12,5%, taglio
  minimo (1 € per le OAT presso quella banca: metterlo in `lot`), rating,
  CAC. **Non contiene il rendimento.**
- Lettura PDF: `python3 -m pip install --user pypdf` poi `PdfReader(path)`.
- Il prezzo della banca è quello realistico di esecuzione: se differisce,
  ricalcolare i netti col prezzo del broker (ogni 0,45 punti di prezzo su
  un 4 anni valgono ~10 bp di rendimento).
- Il fissato bollato dopo l'esecuzione riporta secco, rateo, ritenuta sul
  rateo e commissioni: confrontarlo con la colonna "Esborso" dello script.

## 5. Vie MORTA (non perderci tempo)

| Fonte | Risultato |
| --- | --- |
| Euronext live (`live.euronext.com`) | URL `stock_quote/{ISIN}` → 404; la search API è dietro AWS WAF che non passa |
| BME (`bolsasymercados.es`) pagine issues | la pagina si carica ma la tabella React resta vuota (API SIX non raggiungibile via curl) |
| marketscreener.com | 403 via curl, login wall via browser |
| investing.com | 403 |
| minec.gob.es, deuda.gob.es | inaccessibili da alcune reti (tunnel failure) |
| deust.bde.es | inaccessibile |
| GitHub API | bloccata da alcune reti aziendali (usare il browser) |
| AI Overviews (Google) e chatbot | gli ISIN che danno sono spesso corretti ma **i prezzi possono essere incoerenti/stale**: verificare sempre contro fonte ufficiale + market data |

## 6. Regole operative ricorrenti

- **Prezzi verificati** = letti oggi da btpitalia (BTP) o Yahoo/Euronext (OAT)
  o scheda broker. Tutto il resto = `~ stima` (da curva: interpola gli YTM dei
  prezzi verificati per scadenza e scontare i CF) e va marcato.
- Le quotazioni BTP sono serali (17:39): se ordini la mattina dopo, il prezzo
  cambia; chiedi sempre l'all-in.
- I prezzi quotati sono **corsi secchi**: il rateo si aggiunge
  all'esborso. È un costo vero il giorno dell'acquisto (torna col primo
  stacco) e lo script lo include nel rendimento: non va ignorato.
- Valuta T+2 lavorativi: nel JSON usare `"trade"` con la data dell'ordine.
