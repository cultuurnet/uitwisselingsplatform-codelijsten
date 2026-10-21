# Meetresultaten (QLever, 2026-10-20)

Deze cijfers onderbouwen de severity-keuzes in `shapes/01-core.ttl`.
Hermeet ze voordat je de kernlaag uitbreidt.

## Predicaten op `cidoc:E7_Activity` (2.664.044 instanties)

31 distinct predicaten. Afgezet tegen `ActiviteitShape` uit het huidige
`shacl/cultuurparticipatie_shacl.ttl`:

| | aantal |
|---|---|
| Toegelaten paden in de shape | 40 |
| Daarvan nooit voorkomend in de data | 23 (58%) |
| Voorkomend maar niet in de shape | 13 |
| Triples op die 13 | 27.219.793 |

Herkomst van die 13, nagegaan tegen het OSLO AP en het UWP-template:

| categorie | predicaten | triples | hoort in |
|---|---|---|---|
| Schrijffout tegen een modelterm | `cp:ruimtetijd`, `rdfs:label` (https+www), `cidoc:P4_has_time`, `cp:beschikbaarheid` | 7.471.657 | laag 2 |
| Staat in het UWP-template, maar niet op deze shape | `schema:contactPoint` | 3.596.509 | laag 1 (shape is onvolledig) |
| Aanbieder-specifiek (publiq/UiTdatabank) | `udb:availableFrom`, `udb:workflowStatus`, `udb:audienceType` | 7.378.023 | laag 4 |
| Generiek maar niet gemodelleerd | `dcat:keyword`, `schema:image`, `schema:video`, `skos:relatedMatch`, `skos:exactMatch` | 8.773.604 | ontologie-governance |

Alleen de derde rij is aanbieder-specifiek. De vierde is generiek W3C/schema.org
vocabulaire: dat is een gat in het model, geen publiq-eigenaardigheid.

## Predicaten op `cp:Deelname` per bron (21.670.303 instanties, 6 bronnen)

| bron | deelnames | `uwp:verwerktOp` | `dcterms:modified` | `dcterms:isPartOf` |
|---|---|---|---|---|
| publiq uitpas-checkins | 13.049.828 | 0% | 0% | 0% |
| publiq museumpas-bezoeken | 6.297.136 | 0% | 100% | 100% |
| publiq cultuurconnect-digitaalpodium | 1.317.294 | 100% | 0% | 0% |
| **sirus** yesplan-participatie | 381.007 | 100% | 0% | 0% |
| **sirus** peppered-participatie | 36.811 | 100% | 100% | 0% |
| publiq demo-dataproduct | 1 | 0% | 0% | 0% |

`cp:Deelname` telt in totaal maar 13 distinct predicaten, waarvan er 6 door
nagenoeg alle bronnen gezet worden. De kern is dus klein en gedeeld; de
verschillen zitten in de staart (`dcterms:isPartOf` alleen museumpas,
`peppered:ordered` alleen peppered).

## Shapes die vandaag niets doen

| | aantal |
|---|---|
| NodeShapes in het template | 95 |
| Targeten een klasse met 0 instanties | 33 (142 dode property-constraints) |
| Vuren wel, maar hebben 0 properties (concept-shapes) | 38 |
| **Dragen alle validatie** | **22** |

## Codelijst-waarden per pad

Gemeten 2026-10-20. Onderbouwt de severity in `shapes/03-codelijsten.ttl`.

| klasse | pad | officieel concept | udb-taxonomiecode |
|---|---|---|---|
| `E7_Activity` | `dcterms:type` | 2.194 | 2.618.609 |
| `E7_Activity` | `cp:thema` | 1.420 | 1.372.465 |
| `E7_Activity` | `cp:Activiteit.locatieType` | 2.622.917 | 0 |
| `cp:Deelname` | `dcterms:type` | 19.404.498 | 0 |
| `schema:PriceSpecification` | `cp:Prijsinfo.prijscategorie` | 2.905.202 | 0 |

**Correctie:** die telling was op namespace-niveau en dus te grof - ze zei
niets over welke codelijst een pad gebruikt. Zie de scheme-telling in
validation/README.md: `cp:Activiteit.locatieType` draagt Aanwezigheidsmodus,
niet Locatietype, en er zijn 3 waarden die buiten hun lijst vallen.

**Update 2026-10-21:** de migratie is geland. Alle vijf de paden staan nu op
nul taxonomiecodes (`dcterms:type` 2.769.514 officieel, `cp:thema` 1.442.307,
`Activiteit.locatieType` 2.780.536, `Deelname dcterms:type` 19.729.996,
`Prijsinfo.prijscategorie` 2.108.787).

De codes zijn verhuisd naar `udb:type` (2.775.996) en `udb:theme` (1.444.161),
beide gedeclareerd in de ontologie. `udb:eventType` komt **nergens** in de graph
voor en staat ook niet in de ontologie.

Nieuw op `E7_Activity` en nog niet in de ontologie gedeclareerd:
`udb:typeLabel` (2.776.018), `udb:themeLabel` (1.444.183),
`udb:typicalAgeLowerBound` (1.221.221), `udb:typicalAgeUpperBound` (607.176),
`udb:childrenOnly` (9.400), plus de klasse `udb:SyncState` (5).
