# Validatie-PoC: van open template naar bruikbare feedback

Proof-of-concept bij de vaststelling dat dataproducten vandaag allemaal als
valide door `shacl/cultuurparticipatie_shacl.ttl` komen, ook wanneer er fouten
in zitten. **Dit vervangt dat template niet**; het is een voorstel voor hoe
validatie eruit kan zien, met testdata om het uit te proberen.

## Waarom alles nu valideert

Gemeten tegen de echte graph (zie [`profiling/RESULTATEN.md`](profiling/RESULTATEN.md)):

- 33 van de 95 shapes targeten een klasse die **0 instanties** heeft;
- 38 van de resterende shapes hebben **0 properties** (de concept-shapes);
- op `ActiviteitShape` wijst **58% van de toegelaten paden** naar een property
  die niemand gebruikt, terwijl 13 wél gebruikte predicaten (27,2M triples)
  niet in de shape staan;
- `shacl:minCount` is overal verwijderd, dus aanwezigheid wordt nooit getoetst.

Netto doen 22 shapes al het werk, en die toetsen vooral datatypes.

## De gelaagde opzet

| laag | bestand | bron | aanbieder-neutraal? |
|---|---|---|---|
| 1. Kern | `shapes/01-core.ttl` | OSLO AP + UWP-ontologie | ja |
| 2. Verboden property-URI's | `shapes/02-verboden-properties.ttl` | `variants.json` (gegenereerd) | ja |
| 3. Codelijsten | `shapes/03-codelijsten.ttl` | `../conceptschemes/` (gegenereerd) | ja |
| 4. Uitbreiding per aanbieder | `shapes/ext-*.ttl` | de aanbieder zelf | nee, per bron |
| 4a. UiTdatabank-codes | `shapes/ext-publiq-udb-taxonomie.ttl` | `*.ttl` exactMatch (gegenereerd) | nee, publiq |
| 5. `sh:closed` | nog niet | sluitstuk, pas als 1–4 compleet zijn | ja |

De scheiding tussen laag 1 en laag 4 is wat voorkomt dat de template op één
bron geënt raakt. Een property komt **niet** in de kern omdat een grote bron
ze levert, maar omdat ze in het model staat.

## Codelijst-paden bevatten alleen officiele concepten

In `dcterms:type` en de andere codelijst-paden horen **uitsluitend de officiele
concepten** uit `../conceptschemes/`. De `skos:exactMatch`-varianten
(UiTdatabank-taxonomiecodes) zitten daarom **niet** in laag 3.

Die codes verdwijnen niet: ze zijn verhuisd naar de aanbieder-eigen properties
`udb:type` en `udb:theme`, en krijgen daar hun eigen shapes in laag 4a.
(`udb:eventType` bestaat niet in de data en ook niet in de ontologie; een
eerdere versie van deze PoC mikte daar wel op en valideerde dus niets.) Dat is meteen een goed voorbeeld van waarom de lagen gescheiden zijn:
`udb:` is publiq-vocabulaire en hoort niet in een template dat elke aanbieder
moet kunnen gebruiken.

Gemeten per pad (2026-10-20), met de severity die daaruit volgt:

Gemeten per pad (2026-10-21), met de severity die daaruit volgt:

| klasse | pad | officieel | udb-taxonomie | severity |
|---|---|---|---|---|
| `E7_Activity` | `dcterms:type` | 2.769.514 | 0 | Violation |
| `E7_Activity` | `cp:thema` | 1.442.307 | 0 | Violation |
| `E7_Activity` | `cp:Activiteit.locatieType` | 2.780.536 | 0 | Violation |
| `cp:Deelname` | `dcterms:type` | 19.729.996 | 0 | Violation |
| `schema:PriceSpecification` | `cp:Prijsinfo.prijscategorie` | 2.108.787 | 0 | Violation |

**Alle vijf de paden zijn sinds 21-10 volledig conform**: nul taxonomiecodes.
Op 20-10 stonden `dcterms:type` en `cp:thema` nog op respectievelijk 2.618.609
en 1.372.465 taxonomiecodes. `cp:thema` stond daarom eerst op Warning en kon nu
naar Violation.

## Het meten en de norm uit elkaar houden

Het predicaat-histogram (`profiling/`) is een **meetinstrument, geen norm**.
Het zegt niet wat toegelaten moet zijn; het laat zien waar model en data
uiteenlopen. Elk gevonden predicaat vraagt een beslissing: modelterm (laag 1),
schrijffout (laag 2), aanbieder-eigen (laag 4), of agendapunt voor de ontologie.

Draai het daarom **per bron**, niet alleen over de hele graph. Dat is precies
wat het verschil zichtbaar maakt: `uwp:verwerktOp` staat op 100% bij
cultuurconnect, yesplan en peppered, en op 0% bij uitpas en museumpas. Wie dat
niet uitsplitst, zet die property op Violation en keurt 89,5% van alle
deelnames af.

## Gebruik

```sh
pip install -r ../requirements.txt

# shapes 02, 03 en ext-publiq-udb-eventtype opnieuw genereren na een wijziging
# in variants.json of in conceptschemes/
python generate_shapes.py

# een dataproduct-export valideren
python validate_dataproduct.py testdata/conform.ttl
python validate_dataproduct.py testdata/fouten.ttl

# met de aanbieder-lagen erbij
python validate_dataproduct.py mijn-export.ttl \
  --ext shapes/ext-publiq-uitdatabank.ttl \
  --ext shapes/ext-publiq-udb-taxonomie.ttl

# ook waarschuwingen laten falen
python validate_dataproduct.py mijn-export.ttl --strict
```

Exit-code 0 bij geen Violations. Warnings en Info blokkeren niet.

## Severity als afspraak

- **Violation** — zonder dit is het record onbruikbaar voor elke consumer. Blokkeert.
- **Warning** — consumers verliezen functionaliteit. Blokkeert niet.
- **Info** — volledigheidssignaal voor de dataproduct-owner.

Elke `minCount` in `01-core.ttl` draagt de gemeten dekking als commentaar. Een
property die bij een grote bron structureel ontbreekt, hoort niet op Violation.

> **Let op:** `sh:conforms` uit de SHACL-spec wordt `false` zodra er *enig*
> resultaat is, ongeacht severity. Een CI-gate op `conforms` maakt Warnings dus
> even blokkerend als Violations. `validate_dataproduct.py` gate't daarom zelf
> op `sh:resultSeverity`; met pySHACL rechtstreeks gebruik je `allow_warnings=True`.

## Wat dit nog niet doet

- `sh:closed` (laag 5). Vandaag zou dat op `E7_Activity` 27,2M violations geven,
  waarvan ~72% legitieme verrijking. Eerst de allow-lists compleet maken.
- Dekking buiten Activiteit, Deelname en Participant.
- Twee bekende bugs in het hoofdtemplate zijn hier **niet** gefixt:
  `AlgemeenParticipantKenmerkShape` heeft een targetClass met kleine `k`
  (mist 20.363.961 knopen), en `ActiviteitShape` mist `schema:contactPoint`
  (3.596.509 triples, staat wél in de ontologie).
