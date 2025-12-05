# codelijsten Uitwisselingsplatform

IN PROGRESS: de codelijsten zijn nog niet in gebruik.

Deze repository omvat een aantal codelijsten en de ontologie voor het uitwisselingsplatform https://www.uitwisselingsplatform.be.

## Repository structuur

De repository bevat twee types metadata:

1. **Concept schemes** (`conceptschemes/` directory): Per codelijst wordt een RDF file in de turtle syntax volgens het [SKOS vocabularium](https://www.w3.org/TR/skos-primer/) toegevoegd aan de directory 'conceptschemes'.

2. **Ontologie** (`ontology/` directory): De OWL ontologie die de datamodellen voor het uitwisselingsplatform definieert. De ontologie bestanden worden alleen op syntax gevalideerd (geen SHACL validatie).

# vormafspraken over de codelijsten


- eigenschappen te gebruiken met conceptschemes:

|eigenschap | nota |
|-----------|------|
skos:prefLabel | een unieke naam voor het conceptscheme
skos:definition | een definitie van de codelijst

- eigenschappen te gebruiken met concepts:

|eigenschap | nota |
|-----------|------|
skos:prefLabel | een unieke naam voor het concept
skos:definition | een definitie van het concept
skos:inscheme  | het conceptscheme waartoe dit concept behoort
skos:topConceptOf | het conceptscheme waarvan dit concept een top concept is 
skos:broader | de concepten die boven dit concept hangen in de conceptscheme boom.
skos:exactMatch | verwijzing naar een identiek concept.
skos:related  | verwijzing naar een gerelateerd concept.

- gebruik language-tagged strings i.p.v. plain literals
Dus `"mijn label@nl` i.p.v. `"mijn label"`

- We verwachten een hierarchie in 1 richting. Het is voldoende om de hierarchie in 1 richting uit te drukken. Het is aan de afnemers om indien voor hen nodig ook de omgekeerde relatie te berekenen. Dat maakt de data ook overzichtelijk.

## Validatie

De repository bevat een validatiescript (`check_rdf.py`) dat automatisch wordt uitgevoerd bij elke push of pull request:

- **Concept schemes**: Worden gevalideerd op zowel RDF/Turtle syntax als SHACL shapes (zie `shacl_codelists.ttl`)
- **Ontologie**: Worden alleen gevalideerd op RDF/Turtle syntax (geen SHACL validatie)

Zowel concept schemes als ontologie bestanden moeten geldige Turtle syntax hebben om door de validatie te komen.

