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
| 2b. Verboden classes | `shapes/02b-verboden-klassen.ttl` | `variants.json` (gegenereerd) | ja |
| 3. Codelijsten | `shapes/03-codelijsten.ttl` | `../conceptschemes/` (gegenereerd) | ja |
| 4. Uitbreiding per aanbieder | `shapes/ext-*.ttl` | de aanbieder zelf | nee, per bron |
| 4a. UiTdatabank-codes | `shapes/ext-publiq-udb-taxonomie.ttl` | `*.ttl` exactMatch (gegenereerd) | nee, publiq |
| 5. `sh:closed` | nog niet | sluitstuk, pas als 1–4 compleet zijn | ja |

De scheiding tussen laag 1 en laag 4 is wat voorkomt dat de template op één
bron geënt raakt. Een property komt **niet** in de kern omdat een grote bron
ze levert, maar omdat ze in het model staat.

## Verboden termen: properties en classes

Laag 2 en 2b worden allebei uit `variants.json` gegenereerd en bevatten de
bekende schrijffouten tegen de ontologie. Properties worden afgevangen met
`sh:maxCount 0` op het foute pad; classes met een `sh:targetClass` op de foute
class plus `sh:maxCount 0` op `rdf:type`, wat precies een melding per knoop
geeft.

Classes in de lijst (gemeten 2026-10-21):

| foute class | aantal | hoort te zijn |
|---|---|---|
| `http://schema.org/ContactPoint` | 88.483 | `https://schema.org/ContactPoint` |
| `cp:Activiteit.Beschikbaarheid` | 27.304 | `cp:Beschikbaarheid` |
| `generiek:gestructureerdeIdentificator` | 533 | `generiek:GestructureerdeIdentificator` |
| `sosa:hasResult` | 423 | property, geen class - modelleerbeslissing |
| `gebouw:adres` | 83 | `gebouw:Adres` |
| `dcterms:Organisator` | 71 knopen, 27.552 verwijzingen | `cp:Organisator` |

**Niet met een targetClass te vangen:** een kale term als `a <Tombstone>`
(1.785 knopen in QLever, groeiend). Turtle lost zo'n relatieve IRI op tegen de
base van het bestand, dus bij het inlezen wordt het
`https://data.uitwisselingsplatform.be/id/Tombstone` - een absolute IRI, en per
bestand een andere.

Dat vangt `validate_dataproduct.py` met een eigen controle: elke `rdf:type` die
in de instantie-namespace `.../id/` wijst, wordt gemeld. Legitieme
platform-classes staan in `.../ns/platform#`, dus die regel raakt niets geldigs.
Bewust **geen** SHACL: zie Prestaties hieronder.

In `variants.json` gaat het veld `uitleg` mee in de foutboodschap; `nota`
bevat de meethistoriek en de bron, en blijft uit de boodschap.

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

Gemeten per pad op **scheme-niveau** (2026-10-21):

| klasse | pad | codelijst | waarden | afwijkend |
|---|---|---|---|---|
| `E7_Activity` | `dcterms:type` | ActiviteitType | 2.769.514 | 0 |
| `E7_Activity` | `cp:thema` | ThemaType | 1.442.307 | 0 |
| `E7_Activity` | `cp:Activiteit.locatieType` | **Aanwezigheidsmodus** | 2.780.534 | **2** |
| `dcterms:Location` | `dcterms:type` | **Locatietype** | 260.312 | **1** |
| `cp:Deelname` | `dcterms:type` | DeelnameType | 19.729.996 | 0 |
| `schema:PriceSpecification` | `cp:Prijsinfo.prijscategorie` | PrijsCategorieType | 2.108.787 | 0 |

Alle zes staan op Violation.

### Meet op scheme-niveau, niet op namespace

Een eerdere versie van deze PoC koppelde `cp:Activiteit.locatieType` aan
**Locatietype**, want zo heet de property. Dat is fout: dat pad draagt
**Aanwezigheidsmodus** (fysiek / online / hybride). Locatietype (monument,
sportcentrum, natuurgebied) hoort op `dcterms:Location`.

De fout kon ontstaan doordat de controle te grof was: ik mat of een waarde uit
de namespace `data.cultuurparticipatie.be` kwam en noteerde "100% officiele
concepten". Dat klopte, en zei niets over wélke lijst. Het gevolg was een
Violation-regel die 2,78 miljoen correcte activiteiten afkeurde.

Gebruik daarom `profiling/codelijst-per-pad.rq` voordat je een pad in
`KOPPELING` zet. Die query bracht meteen drie echte datafouten aan het licht:

- 2x `/conceptscheme/Aanwezigheidsmodus/fysiek` in plaats van `/concept/...`
- 1x `/concept/LocatieType/...` met een hoofdletter T

Alle drie staan nu als testgeval in `testdata/fouten.ttl`.

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

## Van vier lagen naar een productiebestand

Het platform koppelt per output port een enkele URL via
`linkedDataSchemaDefinition`, haalt die op en POST de inhoud naar het
`/shacl`-endpoint van de Fuseki dataset:

```js
const body = await (await fetch(shaclUrl)).text();
await fetch('/<dataset>/shacl?graph=union', {
  method: 'POST', headers: { 'Content-Type': 'text/turtle' }, body });
```

Vier bestanden kunnen daar niet heen. De gelaagdheid is dus een **bron**-indeling;
`build_bundle.py` is de distributiestap en schrijft alles naar
`shacl/v1/cultuurparticipatie_shacl.ttl`.

```sh
python build_bundle.py            # bouwen
python build_bundle.py --check    # faalt als de bundel achterloopt (draait in CI)
```

Drie dingen die de bundel bewaakt:

- **`shacl:minCount` in een `ext-*`-laag is verboden.** De bundel gaat naar elke
  aanbieder. Een shape die alleen iets zegt over vocabulaire *die er staat* is
  onschadelijk voor wie die vocabulaire niet levert - dat is waarom een
  publiq-laag mee kan in een template voor iedereen. Een `minCount` breekt die
  eigenschap, dus de build weigert.
- **Prefix-conflicten** tussen lagen (zelfde prefix, andere namespace).
- **Achterlopen**: `--check` vergelijkt de ingecheckte bundel met de lagen.

De huidige `shacl/cultuurparticipatie_shacl.ttl` gaat als **laag 0** mee de
bundel in en wordt niet vervangen: de 22 shapes die daar wel vuren doen
datatype- en `maxCount`-controles op klassen die de nieuwe lagen niet raken.
Opruimen kan daarna, stap voor stap, zonder dat de URL wijzigt.

Het pad heeft bewust een `v1/`: met een vaste URL op `main` slaat elke
aanscherping onmiddellijk in bij alle dataproducten. Op 20-10 zou
`dcterms:type` op Violation 2.618.609 activiteiten hebben afgekeurd; dat is
vandaag nul, maar dat is timing, geen beleid.

## Rapport: elke regel heeft een IRI

Het Fuseki-endpoint geeft een `sh:ValidationReport` terug met per resultaat een
`sh:resultSeverity` en een `sh:sourceShape`. Daarom heeft elke regel in deze
lagen een eigen IRI in plaats van een blank node:

```
sh:resultSeverity  sh:Violation ;
sh:sourceShape     uwpval:VerbodenProp-statistischeSector ;
```

Zo kan het platform groeperen en tellen per regel, in plaats van alleen op de
tekst van de boodschap. Alleen de takken van `sh:or` blijven blank nodes: die
zijn geen zelfstandige regel, en de melding komt van de NodeShape eromheen.

**Gate op `sh:resultSeverity`, niet op `sh:conforms`.** Dat laatste wordt
`false` bij elk resultaat, ook bij een losse Info-melding.

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

## Prestaties

Gemeten op een synthetische export van 50.000 activiteiten (350.007 triples),
met de gepinde pySHACL:

| opzet | tijd |
|---|---|
| alle shape-lagen + de eigen hygiene-controle | **47 s** |
| idem, maar de hygiene-controle als `sh:sparql` met `shacl:targetSubjectsOf rdf:type` | **> 5 min** (afgebroken) |

Dezelfde detectie, meer dan vijf keer zo traag: een SPARQL-constraint maakt elke
getypeerde knoop een focus node en voert de query per knoop uit. Die controle
zit daarom in Python, niet in SHACL.

Reken met die 47 s voor 50.000 activiteiten als je dit inplant. Een volledige
export van 2,8 miljoen activiteiten loopt richting drie kwartier, dus valideer
per dataproduct en bij voorkeur incrementeel op wat er gewijzigd is - niet elke
nacht de hele graph.

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
