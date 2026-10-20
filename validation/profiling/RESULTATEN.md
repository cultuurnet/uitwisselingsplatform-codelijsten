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
