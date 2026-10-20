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
| 4a. UiTdatabank-codes | `shapes/ext-publiq-udb-eventtype.ttl` | `Activiteittype.ttl` exactMatch (gegenereerd) | nee, publiq |
| 5. `sh:closed` | nog niet | sluitstuk, pas als 1–4 compleet zijn | ja |

De scheiding tussen laag 1 en laag 4 is wat voorkomt dat de template op één
bron geënt raakt. Een property komt **niet** in de kern omdat een grote bron
ze levert, maar omdat ze in het model staat.

## Codelijst-paden bevatten alleen officiele concepten

In `dcterms:type` en de andere codelijst-paden horen **uitsluitend de officiele
concepten** uit `../conceptschemes/`. De `skos:exactMatch`-varianten
(UiTdatabank-taxonomiecodes) zitten daarom **niet** in laag 3.

Die codes verdwijnen niet: ze zijn in de nieuwe datasets verhuisd naar de
aanbieder-eigen property `udb:eventType`, en krijgen daar hun eigen shape in
laag 4a. Dat is meteen een goed voorbeeld van waarom de lagen gescheiden zijn:
`udb:` is publiq-vocabulaire en hoort niet in een template dat elke aanbieder
moet kunnen gebruiken.

Gemeten per pad (2026-10-20), met de severity die daaruit volgt:

| klasse | pad | officieel | udb-taxonomie | severity |
|---|---|---|---|---|
| `E7_Activity` | `dcterms:type` | 2.194 | 2.618.609 | Violation |
| `E7_Activity` | `cp:thema` | 1.420 | 1.372.465 | Warning |
| `E7_Activity` | `cp:Activiteit.locatieType` | 2.622.917 | 0 | Violation |
| `cp:Deelname` | `dcterms:type` | 19.404.498 | 0 | Violation |
| `schema:PriceSpecification` | `cp:Prijsinfo.prijscategorie` | 2.905.202 | 0 | Violation |

Drie van de vijf paden zijn dus al volledig conform. `dcterms:type` staat op
Violation omdat de regel vaststaat en de doelproperty bestaat; de 2,6M bestaande
taxonomiecodes zijn migratieschuld, geen reden om de regel te verzachten.

**Open punt:** `cp:thema` heeft hetzelfde probleem (1.372.465 taxonomiecodes),
maar er is nog geen afgesproken doelproperty zoals `udb:eventType`. Daarom staat
dat pad voorlopig op Warning. Zodra de naam vastligt, kan het naar Violation en
komt er een tweede gegenereerde shape in laag 4a.

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
  --ext shapes/ext-publiq-udb-eventtype.ttl

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
