#!/usr/bin/env python3
"""Genereert de twee shape-lagen die uit een bron afgeleid kunnen worden.

  shapes/02-verboden-properties.ttl  <- variants.json
  shapes/03-codelijsten.ttl          <- ../conceptschemes/*.ttl (officiele concepten)
  shapes/ext-publiq-udb-eventtype.ttl <- ../conceptschemes/Activiteittype.ttl (exactMatch)

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
    for i, (klasse, items) in enumerate(sorted(per_klasse.items()), start=1):
        naam = klasse.split("#")[-1].split("/")[-1]
        props = []
        for v in items:
            nota = f" {v['nota']}." if v.get("nota") else ""
            boodschap = (
                f"Foute property-URI <{v['fout']}>.{nota} "
                f"Gebruik <{v['correct']}>."
            )
            props.append(
                f"""  shacl:property [
    shacl:path <{v['fout']}> ;
    shacl:maxCount 0 ;
    shacl:severity shacl:Violation ;
    shacl:message "{boodschap}" ] ;"""
            )
        uit.append(
            f"""uwpval:VerbodenProperties{naam} a shacl:NodeShape ;
  shacl:targetClass <{klasse}> ;
{chr(10).join(props)}
  shacl:name "Verboden property-URI's op {naam}"@nl .

"""
        )
    pad = os.path.join(SHAPES, "02-verboden-properties.ttl")
    with open(pad, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad, HIER)} "
          f"({len(varianten)} varianten over {len(per_klasse)} klassen)")


# Welke codelijst hoort bij welk pad, met de severity en de meting die haar
# onderbouwt (QLever, 2026-10-20: officiele concepten / udb-taxonomiecodes).
#
# REGEL: in dcterms:type en de andere codelijst-paden horen UITSLUITEND de
# officiele concepten uit de codelijsten. Een UiTdatabank-taxonomiecode hoort
# in de aanbieder-eigen property udb:eventType - zie genereer_udb_eventtype().
KOPPELING = [
    # (codelijst, targetClass, pad, severity, meting)
    ("Activiteittype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "http://purl.org/dc/terms/type", "Violation",
     "2.194 officieel / 2.618.609 taxonomie - de taxonomiecodes horen in udb:eventType"),
    ("ThemaType.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#thema", "Warning",
     "1.420 officieel / 1.372.465 taxonomie - nog geen afgesproken doelproperty, daarom Warning"),
    ("Locatietype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#Activiteit.locatieType", "Violation",
     "2.622.917 officieel / 0 taxonomie - al conform"),
    ("DeelnameType.ttl", "https://data.vlaanderen.be/ns/cultuurparticipatie#Deelname",
     "http://purl.org/dc/terms/type", "Violation",
     "19.404.498 officieel / 0 taxonomie - al conform"),
    ("PrijsCategorieType.ttl", "https://schema.org/PriceSpecification",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#Prijsinfo.prijscategorie", "Violation",
     "2.905.202 officieel / 0 taxonomie - al conform"),
]

# De taxonomiecodes zijn GEEN geldige waarde in de codelijst-paden, maar ze
# blijven wel bestaan als aanbieder-eigen gegeven. Dit is hun enige geldige plek.
UDB_EVENTTYPE = ("Activiteittype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
                 "https://data.publiq.be/ns/uitdatabank#eventType", "Warning")


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
    shape op udb:eventType in de aanbieder-laag.
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
        extra = (" Een UiTdatabank-taxonomiecode hoort hier niet: zet die in udb:eventType."
                 if pad.endswith("terms/type") or pad.endswith("#thema") else "")
        uit.append(
            f"""# {bestand}: {len(concepten)} officiele concepten (de {len(matches)} exactMatch-varianten
# horen NIET in dit pad). Meting: {meting}
uwpval:Codelijst{naam} a shacl:NodeShape ;
  shacl:targetClass <{klasse}> ;
  shacl:property [
    shacl:path <{pad}> ;
    shacl:in (
      {waarden} ) ;
    shacl:severity shacl:{severity} ;
    shacl:message "Waarde zit niet in codelijst {lijst}. Alleen officiele concepten uit data.cultuurparticipatie.be zijn toegelaten.{extra}" ] .

"""
        )
        totaal += len(concepten)
        print(f"  {bestand}: {len(concepten)} concepten -> {pad.split('#')[-1].split('/')[-1]} ({severity})")
    pad_uit = os.path.join(SHAPES, "03-codelijsten.ttl")
    with open(pad_uit, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad_uit, HIER)} ({totaal} concepten totaal)")


def genereer_udb_eventtype():
    """Laag 4 (publiq): de UiTdatabank-taxonomiecodes op udb:eventType.

    Aanbieder-specifiek, dus apart van de kern. Dit is waar de codes naartoe
    verhuisd zijn nu ze niet meer in dcterms:type mogen staan.
    """
    bestand, klasse, pad, severity = UDB_EVENTTYPE
    concepten, matches = _concepten(bestand)
    if not matches:
        print(f"  OVERGESLAGEN: {bestand} heeft geen skos:exactMatch")
        return
    waarden = "\n      ".join(f"<{u}>" for u in matches)
    uit = [HEADER.format(bron=f"../conceptschemes/{bestand} (skos:exactMatch)")]
    uit.append(
        f"""# {len(matches)} UiTdatabank-taxonomiecodes, afgeleid van de skos:exactMatch
# in {bestand}. Aanbieder-specifiek (publiq/UiTdatabank): hoort NIET in de kern.
uwpval:ExtPubliqEventType a shacl:NodeShape ;
  shacl:targetClass <{klasse}> ;
  shacl:name "UiTdatabank-taxonomiecode op udb:eventType"@nl ;
  shacl:property [
    shacl:path <{pad}> ;
    shacl:in (
      {waarden} ) ;
    shacl:severity shacl:{severity} ;
    shacl:message "udb:eventType bevat een code die niet via skos:exactMatch aan codelijst ActiviteitType hangt." ] .

"""
    )
    pad_uit = os.path.join(SHAPES, "ext-publiq-udb-eventtype.ttl")
    with open(pad_uit, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad_uit, HIER)} ({len(matches)} taxonomiecodes)")


if __name__ == "__main__":
    os.makedirs(SHAPES, exist_ok=True)
    print("### verboden properties ###")
    genereer_verboden_properties()
    print("### codelijsten ###")
    genereer_codelijsten()
    print("### udb:eventType (aanbieder-laag) ###")
    genereer_udb_eventtype()
