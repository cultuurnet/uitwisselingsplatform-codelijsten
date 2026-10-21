#!/usr/bin/env python3
"""Valideert een dataproduct-export tegen de gelaagde UWP-shapes.

    python validate_dataproduct.py <data.ttl> [--ext shapes/ext-publiq-uitdatabank.ttl]
                                              [--strict] [--shapes-dir shapes]

Exit-code 0 als er geen Violations zijn. Warnings en Info blokkeren niet,
tenzij --strict.

LET OP: sh:conforms uit SHACL is false zodra er EEN resultaat is, ongeacht
severity. Wie op conforms gate't, maakt Warnings even blokkerend als
Violations. Daarom gate't dit script zelf op sh:resultSeverity.
"""
import argparse
import glob
import os
import sys
from collections import Counter, defaultdict

from pyshacl import validate
from rdflib import Graph, Namespace, URIRef

SH = Namespace("http://www.w3.org/ns/shacl#")
RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
INSTANTIE_NS = "https://data.uitwisselingsplatform.be/id/"
VOLGORDE = ["Violation", "Warning", "Info"]


def hygiene_classes(data):
    """Class-IRI's die in de instantie-namespace staan.

    Dit vangt het geval dat een shape niet kan vangen: een kale term als
    `a <Tombstone>` lost bij het parsen op tegen de base van het bestand en
    wordt dan <.../id/Tombstone> - absolute IRI, maar in de namespace waar
    instanties wonen. De class verschilt per bestand, dus een vaste
    shacl:targetClass werkt niet.

    Bewust GEEN SHACL: als sh:sparql met shacl:targetSubjectsOf rdf:type
    gekost dit op 50.000 knopen meer dan vijf minuten, tegen 48 seconden voor
    de rest samen. Deze lus doet hetzelfde in milliseconden.
    """
    gevonden = Counter()
    for t in data.objects(None, RDF_TYPE):
        if isinstance(t, URIRef) and str(t).startswith(INSTANTIE_NS):
            gevonden[str(t)] += 1
    return gevonden


def laad_shapes(shapes_dir, extra):
    """Alle genummerde lagen + optionele aanbieder-uitbreidingen in een graph."""
    g = Graph()
    bestanden = sorted(glob.glob(os.path.join(shapes_dir, "0*.ttl"))) + list(extra)
    for b in bestanden:
        g.parse(b, format="turtle")
    return g, bestanden


def main():
    p = argparse.ArgumentParser()
    p.add_argument("data")
    p.add_argument("--ext", action="append", default=[],
                   help="aanbieder-specifiek shapes-bestand (meermaals toegestaan)")
    p.add_argument("--shapes-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes"))
    p.add_argument("--strict", action="store_true", help="laat ook Warnings falen")
    args = p.parse_args()

    data = Graph()
    data.parse(args.data, format="turtle")
    shapes, bestanden = laad_shapes(args.shapes_dir, args.ext)

    print(f"data   : {args.data} ({len(data)} triples)")
    print(f"shapes : {', '.join(os.path.basename(b) for b in bestanden)}")
    print()

    _, rapport, _ = validate(data, shacl_graph=shapes, inference="none", advanced=True)

    # groepeer per severity en per boodschap, zodat 10.000 keer dezelfde fout
    # een regel is en geen muur tekst
    per_sev = defaultdict(Counter)
    for r in rapport.subjects(SH.resultSeverity, None):
        sev = str(rapport.value(r, SH.resultSeverity)).split("#")[-1]
        msg = rapport.value(r, SH.resultMessage)
        pad = rapport.value(r, SH.resultPath)
        sleutel = str(msg) if msg else f"(geen boodschap) pad={pad}"
        per_sev[sev][sleutel] += 1

    for klasse, n in hygiene_classes(data).items():
        per_sev["Violation"][
            f"rdf:type verwijst naar <{klasse}>, een IRI in de instantie-namespace "
            f"({INSTANTIE_NS}). Daar wonen instanties, geen classes - vaak het gevolg "
            f"van een relatieve IRI zoals 'a <Tombstone>' die tegen de base is opgelost."
        ] += n

    totalen = {s: sum(per_sev[s].values()) for s in VOLGORDE}
    for sev in VOLGORDE:
        if not per_sev[sev]:
            continue
        merk = {"Violation": "FOUT", "Warning": "WAARSCHUWING", "Info": "INFO"}[sev]
        print(f"### {merk} ({totalen[sev]})")
        for msg, n in per_sev[sev].most_common():
            print(f"  {n:>6}x  {msg}")
        print()

    if not any(totalen.values()):
        print("Geen bevindingen.")

    print(f"samenvatting: {totalen['Violation']} fout, "
          f"{totalen['Warning']} waarschuwing, {totalen['Info']} info")

    faal = totalen["Violation"] > 0 or (args.strict and totalen["Warning"] > 0)
    return 1 if faal else 0


if __name__ == "__main__":
    sys.exit(main())
