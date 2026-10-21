#!/usr/bin/env python3
"""Genereert de twee shape-lagen die uit een bron afgeleid kunnen worden.

  shapes/02-verboden-properties.ttl  <- variants.json (properties)
  shapes/02b-verboden-klassen.ttl    <- variants.json (classes)
  shapes/03-codelijsten.ttl          <- ../conceptschemes/*.ttl (officiele concepten)
  shapes/ext-publiq-udb-taxonomie.ttl <- ../conceptschemes/*.ttl (exactMatch -> udb:type/udb:theme)

Beide zijn GEGENEREERD: niet met de hand aanpassen, maar de bron wijzigen en
dit script opnieuw draaien. Zo rot de lijst niet mee met de codelijsten.

Gebruik:  python generate_shapes.py
"""
import json
import os
from rdflib import Graph, Namespace, RDF, URIRef

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
HIER = os.path.dirname(os.path.abspath(__file__))
SHAPES = os.path.join(HIER, "shapes")

def slug(uri):
    """Korte, stabiele naam voor een property-shape-IRI, afgeleid van het pad.

    Zodat sh:sourceShape in het validatierapport herleidbaar is naar een regel
    in plaats van een blank node. Het Fuseki /shacl-endpoint geeft die IRI
    letterlijk terug, dus het platform kan erop groeperen en ernaar linken.
    """
    kern = uri.split("#")[-1] if "#" in uri else uri.rstrip("/").split("/")[-1]
    veilig = "".join(c if (c.isalnum() or c in "-_") else "-" for c in kern)
    return veilig.strip("-")


HEADER = """# GEGENEREERD door validation/generate_shapes.py - niet met de hand aanpassen.
# Bron: {bron}

@prefix shacl: <http://www.w3.org/ns/shacl#> .
@prefix uwpval: <https://data.uitwisselingsplatform.be/doc/validatie#> .

"""


def genereer_verboden_properties():
    """Laag 2: elke bekende foute property-URI als sh:maxCount 0, met de juiste vorm erbij."""
    bron = os.path.join(HIER, "variants.json")
    with open(bron, encoding="utf-8") as f:
        varianten = json.load(f)["properties"]

    # groepeer per klasse: een shape per targetClass
    per_klasse = {}
    for v in varianten:
        per_klasse.setdefault(v["klasse"], []).append(v)

    uit = [HEADER.format(bron="variants.json")]
    losse = []
    for i, (klasse, items) in enumerate(sorted(per_klasse.items()), start=1):
        naam = klasse.split("#")[-1].split("/")[-1]
        props = []
        for v in items:
            uitleg = f" {v['uitleg']}" if v.get("uitleg") else ""
            boodschap = (
                f"Foute property-URI <{v['fout']}>.{uitleg} "
                f"Gebruik <{v['correct']}>."
            )
            ps_iri = f"uwpval:VerbodenProp-{slug(v['fout'])}"
            props.append(
                f"""  shacl:property {ps_iri} ;"""
            )
            losse.append(
                f"""{ps_iri} a shacl:PropertyShape ;
  shacl:path <{v['fout']}> ;
  shacl:maxCount 0 ;
  shacl:severity shacl:Violation ;
  shacl:message "{boodschap}" .

"""
            )
        uit.append(
            f"""uwpval:VerbodenProperties{naam} a shacl:NodeShape ;
  shacl:targetClass <{klasse}> ;
{chr(10).join(props)}
  shacl:name "Verboden property-URI's op {naam}"@nl .

"""
        )
    uit.extend(losse)
    pad = os.path.join(SHAPES, "02-verboden-properties.ttl")
    with open(pad, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad, HIER)} "
          f"({len(varianten)} varianten over {len(per_klasse)} klassen)")



def genereer_verboden_klassen():
    """Laag 2b: classes die niet gebruikt mogen worden.

    Een knoop wordt gevonden via shacl:targetClass op de FOUTE class, en faalt
    dan altijd op rdf:type met maxCount 0. Dat geeft precies een melding per
    knoop, met de juiste class in de boodschap.

    Werkt alleen voor classes met een absolute IRI. Een kale term als
    'Tombstone' lost bij het parsen op tegen de base van het bestand en is dus
    niet met een vaste targetClass te vangen - zie de regel over de
    instantie-namespace in 01-core.ttl.
    """
    bron = os.path.join(HIER, "variants.json")
    with open(bron, encoding="utf-8") as f:
        klassen = json.load(f).get("classes", [])
    if not klassen:
        print("  geen classes in variants.json")
        return

    uit = [HEADER.format(bron="variants.json (classes)")]
    uit.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n\n")
    for i, k in enumerate(klassen, start=1):
        uitleg = f" {k['uitleg']}" if k.get("uitleg") else ""
        if k.get("correct"):
            advies = f" Gebruik <{k['correct']}>."
        else:
            advies = " Er is geen vervangende class afgesproken: dit vraagt een modelleerbeslissing."
        boodschap = f"Verboden class <{k['fout']}>.{uitleg}{advies}"
        naam = slug(k["fout"])
        uit.append(
            f"""# gemeten {k.get('gemeten_op', '?')}: {k['gemeten']}
uwpval:VerbodenKlasse-{naam} a shacl:NodeShape ;
  shacl:targetClass <{k['fout']}> ;
  shacl:property uwpval:VerbodenKlasseRegel-{naam} .

uwpval:VerbodenKlasseRegel-{naam} a shacl:PropertyShape ;
  shacl:path rdf:type ;
  shacl:maxCount 0 ;
  shacl:severity shacl:Violation ;
  shacl:message "{boodschap}" .

"""
        )
    pad_uit = os.path.join(SHAPES, "02b-verboden-klassen.ttl")
    with open(pad_uit, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad_uit, HIER)} ({len(klassen)} classes)")


# Welke codelijst hoort bij welk pad, met de severity en de meting die haar
# onderbouwt (QLever, 2026-10-20: officiele concepten / udb-taxonomiecodes).
#
# REGEL: in dcterms:type en de andere codelijst-paden horen UITSLUITEND de
# officiele concepten uit de codelijsten. Een UiTdatabank-taxonomiecode hoort
# in de aanbieder-eigen properties udb:type / udb:theme - zie genereer_udb_taxonomie().
KOPPELING = [
    # (codelijst, targetClass, pad, severity, meting)
    ("Activiteittype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "http://purl.org/dc/terms/type", "Violation",
     "2026-10-21: 2.769.514 officieel / 0 taxonomie - migratie afgerond"),
    ("ThemaType.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#thema", "Violation",
     "2026-10-21: 1.442.307 officieel / 0 taxonomie - migratie afgerond; op 20-10 "
     "was dit nog 1.420 / 1.372.465 en stond het pad daarom op Warning"),
    ("Locatietype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#Activiteit.locatieType", "Violation",
     "2026-10-21: 2.780.536 officieel / 0 taxonomie"),
    ("DeelnameType.ttl", "https://data.vlaanderen.be/ns/cultuurparticipatie#Deelname",
     "http://purl.org/dc/terms/type", "Violation",
     "2026-10-21: 19.729.996 officieel / 0 taxonomie"),
    ("PrijsCategorieType.ttl", "https://schema.org/PriceSpecification",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#Prijsinfo.prijscategorie", "Violation",
     "2026-10-21: 2.108.787 officieel / 0 taxonomie"),
]

# De taxonomiecodes zijn GEEN geldige waarde in de codelijst-paden, maar ze
# blijven wel bestaan als aanbieder-eigen gegeven. Dit is hun enige geldige plek.
#
# De properties heten udb:type en udb:theme - NIET udb:eventType. Gemeten
# 2026-10-21: udb:type 2.775.996, udb:theme 1.444.161, udb:eventType 0 (komt
# nergens in de graph voor). Beide staan zo ook in ontology/owl-uwp-oslo-cp.ttl.
UDB_TAXONOMIE = [
    # (codelijst, targetClass, pad, severity, meting)
    ("Activiteittype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.publiq.be/ns/uitdatabank#type", "Warning",
     "2026-10-21: 2.775.996 taxonomie-IRIs"),
    ("ThemaType.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.publiq.be/ns/uitdatabank#theme", "Warning",
     "2026-10-21: 1.444.161 taxonomie-IRIs"),
]

def _concepten(bestand):
    """(concepten, exactMatch-varianten) uit een codelijst."""
    bron = os.path.join(HIER, "..", "conceptschemes", bestand)
    if not os.path.exists(bron):
        return None, None
    g = Graph()
    g.parse(bron, format="turtle")
    concepten = sorted(str(c) for c in g.subjects(RDF.type, SKOS.Concept))
    matches = sorted(
        {str(m) for c in g.subjects(RDF.type, SKOS.Concept)
         for m in g.objects(URIRef(c), SKOS.exactMatch)}
    )
    return concepten, matches


def genereer_codelijsten():
    """Laag 3: sh:in per codelijst met UITSLUITEND de officiele concepten.

    De skos:exactMatch-varianten (UiTdatabank-taxonomiecodes) zitten hier
    bewust NIET in: die horen niet in dcterms:type thuis. Ze krijgen hun eigen
    shapes op udb:type / udb:theme in de aanbieder-laag.
    """
    uit = [HEADER.format(bron="../conceptschemes/*.ttl")]
    totaal = 0
    for bestand, klasse, pad, severity, meting in KOPPELING:
        concepten, matches = _concepten(bestand)
        if concepten is None:
            print(f"  OVERGESLAGEN: {bestand} bestaat niet")
            continue
        if not concepten:
            print(f"  OVERGESLAGEN: {bestand} bevat geen skos:Concept")
            continue
        waarden = "\n      ".join(f"<{u}>" for u in concepten)
        lijst = bestand.replace(".ttl", "")
        naam = f"{klasse.split('#')[-1].split('/')[-1]}_{pad.split('#')[-1].split('/')[-1]}"
        # noem de juiste doelproperty, afgeleid uit UDB_TAXONOMIE (zelfde
        # codelijst + klasse), zodat de boodschap klopt per pad
        doel = next((u_pad for u_best, u_kl, u_pad, _, _ in UDB_TAXONOMIE
                     if u_best == bestand and u_kl == klasse), None)
        extra = (f" Een UiTdatabank-taxonomiecode hoort hier niet: zet die in "
                 f"udb:{doel.split('#')[-1]}." if doel else "")
        uit.append(
            f"""# {bestand}: {len(concepten)} officiele concepten (de {len(matches)} exactMatch-varianten
# horen NIET in dit pad). Meting: {meting}
uwpval:Codelijst{naam} a shacl:NodeShape ;
  shacl:targetClass <{klasse}> ;
  shacl:property uwpval:CodelijstRegel{naam} .

uwpval:CodelijstRegel{naam} a shacl:PropertyShape ;
  shacl:path <{pad}> ;
  shacl:in (
      {waarden} ) ;
  shacl:severity shacl:{severity} ;
  shacl:message "Waarde zit niet in codelijst {lijst}. Alleen officiele concepten uit data.cultuurparticipatie.be zijn toegelaten.{extra}" .

"""
        )
        totaal += len(concepten)
        print(f"  {bestand}: {len(concepten)} concepten -> {pad.split('#')[-1].split('/')[-1]} ({severity})")
    pad_uit = os.path.join(SHAPES, "03-codelijsten.ttl")
    with open(pad_uit, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad_uit, HIER)} ({totaal} concepten totaal)")


def genereer_udb_taxonomie():
    """Laag 4a (publiq): de UiTdatabank-taxonomiecodes op udb:type en udb:theme.

    Aanbieder-specifiek, dus apart van de kern. Dit is waar de codes naartoe
    verhuisd zijn nu ze niet meer in dcterms:type en cp:thema mogen staan.
    """
    uit = [HEADER.format(bron="../conceptschemes/*.ttl (skos:exactMatch)")]
    geschreven = 0
    for bestand, klasse, pad, severity, meting in UDB_TAXONOMIE:
        _, matches = _concepten(bestand)
        if not matches:
            print(f"  OVERGESLAGEN: {bestand} heeft geen skos:exactMatch")
            continue
        waarden = "\n      ".join(f"<{u}>" for u in matches)
        lokaal = pad.split("#")[-1]
        lijst = bestand.replace(".ttl", "")
        uit.append(
            f"""# {len(matches)} UiTdatabank-taxonomiecodes uit {bestand} (skos:exactMatch).
# Aanbieder-specifiek (publiq/UiTdatabank): hoort NIET in de kern. Meting: {meting}
uwpval:ExtPubliqUdb{lokaal[0].upper()}{lokaal[1:]} a shacl:NodeShape ;
  shacl:targetClass <{klasse}> ;
  shacl:name "UiTdatabank-taxonomiecode op udb:{lokaal}"@nl ;
  shacl:property uwpval:ExtPubliqUdbRegel-{lokaal} .

uwpval:ExtPubliqUdbRegel-{lokaal} a shacl:PropertyShape ;
  shacl:path <{pad}> ;
  shacl:in (
      {waarden} ) ;
  shacl:severity shacl:{severity} ;
  shacl:message "udb:{lokaal} bevat een code die niet via skos:exactMatch aan codelijst {lijst} hangt." .

"""
        )
        geschreven += 1
        print(f"  {bestand}: {len(matches)} taxonomiecodes -> udb:{lokaal} ({severity})")
    pad_uit = os.path.join(SHAPES, "ext-publiq-udb-taxonomie.ttl")
    with open(pad_uit, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad_uit, HIER)} ({geschreven} shapes)")


if __name__ == "__main__":
    os.makedirs(SHAPES, exist_ok=True)
    print("### verboden properties ###")
    genereer_verboden_properties()
    print("### verboden klassen ###")
    genereer_verboden_klassen()
    print("### codelijsten ###")
    genereer_codelijsten()
    print("### udb-taxonomiecodes (aanbieder-laag) ###")
    genereer_udb_taxonomie()
