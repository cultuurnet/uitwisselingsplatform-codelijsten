#!/usr/bin/env python3
"""Genereert de twee shape-lagen die uit een bron afgeleid kunnen worden.

  shapes/02-verboden-properties.ttl  <- variants.json
  shapes/03-codelijsten.ttl          <- ../conceptschemes/*.ttl

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


# Welke codelijst hoort bij welk pad. Alleen paden waarvan de codelijst
# volledig is: een onvolledige lijst levert vals alarm op.
KOPPELING = [
    # (codelijst-bestand, targetClass, pad)
    ("Activiteittype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "http://purl.org/dc/terms/type"),
    ("ThemaType.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#thema"),
    ("Locatietype.ttl", "http://www.cidoc-crm.org/cidoc-crm/E7_Activity",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#Activiteit.locatieType"),
    ("DeelnameType.ttl", "https://data.vlaanderen.be/ns/cultuurparticipatie#Deelname",
     "http://purl.org/dc/terms/type"),
    ("PrijsCategorieType.ttl", "https://schema.org/PriceSpecification",
     "https://data.vlaanderen.be/ns/cultuurparticipatie#Prijsinfo.prijscategorie"),
]


def genereer_codelijsten():
    """Laag 3: sh:in per codelijst, inclusief de skos:exactMatch-varianten.

    De exactMatch-tak is er voor de overgangsperiode: de data draagt vandaag de
    UiTdatabank-taxonomiecode in dcterms:type. Na de datamigratie mag die tak weg
    en kan de severity naar Violation.
    """
    uit = [HEADER.format(bron="../conceptschemes/*.ttl")]
    totaal = 0
    for bestand, klasse, pad in KOPPELING:
        bron = os.path.join(HIER, "..", "conceptschemes", bestand)
        if not os.path.exists(bron):
            print(f"  OVERGESLAGEN: {bestand} bestaat niet")
            continue
        g = Graph()
        g.parse(bron, format="turtle")
        concepten = sorted(str(c) for c in g.subjects(RDF.type, SKOS.Concept))
        matches = sorted(
            {str(m) for c in g.subjects(RDF.type, SKOS.Concept)
             for m in g.objects(URIRef(c), SKOS.exactMatch)}
        )
        if not concepten:
            print(f"  OVERGESLAGEN: {bestand} bevat geen skos:Concept")
            continue
        waarden = "\n      ".join(f"<{u}>" for u in concepten + matches)
        lijst = bestand.replace(".ttl", "")
        naam = f"{klasse.split('#')[-1].split('/')[-1]}_{pad.split('#')[-1].split('/')[-1]}"
        uit.append(
            f"""# {bestand}: {len(concepten)} concepten + {len(matches)} exactMatch-varianten
uwpval:Codelijst{naam} a shacl:NodeShape ;
  shacl:targetClass <{klasse}> ;
  shacl:property [
    shacl:path <{pad}> ;
    shacl:in (
      {waarden} ) ;
    shacl:severity shacl:Warning ;
    shacl:message "Waarde zit niet in codelijst {lijst}. Gebruik een officieel concept uit data.cultuurparticipatie.be, of de UiTdatabank-code die er via skos:exactMatch aan hangt." ] .

"""
        )
        totaal += len(concepten)
        print(f"  {bestand}: {len(concepten)} concepten, {len(matches)} exactMatch")
    pad_uit = os.path.join(SHAPES, "03-codelijsten.ttl")
    with open(pad_uit, "w", encoding="utf-8") as f:
        f.write("".join(uit))
    print(f"  geschreven: {os.path.relpath(pad_uit, HIER)} ({totaal} concepten totaal)")


if __name__ == "__main__":
    os.makedirs(SHAPES, exist_ok=True)
    print("### verboden properties ###")
    genereer_verboden_properties()
    print("### codelijsten ###")
    genereer_codelijsten()
