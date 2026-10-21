#!/usr/bin/env python3
"""Bouwt de losse shape-lagen tot EEN SHACL-bestand voor productie.

Het platform koppelt per output port een enkele URL via
`linkedDataSchemaDefinition` en POST de inhoud daarvan naar het
/shacl-endpoint van de Fuseki dataset. Vier bestanden kunnen daar niet heen,
dus de gelaagdheid is een BRON-indeling en dit is de distributiestap.

    python build_bundle.py                 # bouwt shacl/v1/cultuurparticipatie_shacl.ttl
    python build_bundle.py --check         # faalt als de bundel niet meer klopt

Waarom tekstueel samenvoegen en niet parsen+serialiseren: de commentaren in de
lagen dragen de onderbouwing (gemeten dekking, bron van een fout), en die wil
je kunnen lezen als je de URL opent. Bovendien is concatenatie deterministisch,
wat de --check in CI betrouwbaar maakt.
"""
import argparse
import datetime
import glob
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
SHAPES = os.path.join(HIER, "shapes")
LEGACY = os.path.join(REPO, "shacl", "cultuurparticipatie_shacl.ttl")
UIT = os.path.join(REPO, "shacl", "v1", "cultuurparticipatie_shacl.ttl")

PREFIX_RE = re.compile(r"^@prefix\s+([A-Za-z0-9_-]*):\s*<([^>]*)>\s*\.", re.M)


def lagen():
    """Laag 0 (huidig template) + de genummerde lagen + de aanbieder-lagen."""
    uit = []
    if os.path.exists(LEGACY):
        uit.append(("0-legacy", LEGACY))
    for f in sorted(glob.glob(os.path.join(SHAPES, "0*.ttl"))):
        uit.append((os.path.basename(f), f))
    for f in sorted(glob.glob(os.path.join(SHAPES, "ext-*.ttl"))):
        uit.append((os.path.basename(f), f))
    return uit


def controleer_aanbieder_lagen(bestanden):
    """Een aanbieder-laag mag nooit aanwezigheid eisen.

    De bundel gaat naar ELKE aanbieder. Een shape die alleen iets zegt over
    vocabulaire DIE ER STAAT, is onschadelijk voor wie die vocabulaire niet
    levert. Een shacl:minCount verandert dat: dan leg je het profiel van een
    bron op aan de rest. Dat mag de build niet laten passeren.
    """
    fouten = []
    for naam, pad in bestanden:
        if not naam.startswith("ext-"):
            continue
        with open(pad, encoding="utf-8") as f:
            for nr, regel in enumerate(f, start=1):
                if "shacl:minCount" in regel and not regel.lstrip().startswith("#"):
                    fouten.append(f"{naam}:{nr}: {regel.strip()}")
    return fouten


def controleer_prefixen(bestanden):
    """Zelfde prefix met een andere namespace tussen lagen is een stille bug."""
    gezien, fouten = {}, []
    for naam, pad in bestanden:
        with open(pad, encoding="utf-8") as f:
            for prefix, ns in PREFIX_RE.findall(f.read()):
                if prefix in gezien and gezien[prefix][1] != ns:
                    fouten.append(
                        f"prefix '{prefix}:' is <{gezien[prefix][1]}> in {gezien[prefix][0]} "
                        f"maar <{ns}> in {naam}")
                gezien.setdefault(prefix, (naam, ns))
    return fouten


def bouw(bestanden):
    vandaag = datetime.date.today().isoformat()
    kop = [
        "####",
        "# UWP SHACL - cultuurparticipatie, gebundeld voor productie.",
        "#",
        "# GEGENEREERD door validation/build_bundle.py - niet met de hand aanpassen.",
        f"# Gebouwd op {vandaag} uit de volgende lagen:",
    ]
    for naam, _ in bestanden:
        kop.append(f"#   - {naam}")
    kop += [
        "#",
        "# De bron en de onderbouwing per regel staan in validation/ in deze repo.",
        "# Elke regel heeft een eigen IRI, zodat sh:sourceShape in het validatie-",
        "# rapport herleidbaar is naar een regel in plaats van een blank node.",
        "#",
        "# Severity: Violation blokkeert, Warning en Info niet. Let op dat",
        "# sh:conforms false wordt bij ELK resultaat, ongeacht severity - gate dus",
        "# op sh:resultSeverity, niet op sh:conforms.",
        "####",
        "",
    ]
    delen = ["\n".join(kop)]
    for naam, pad in bestanden:
        with open(pad, encoding="utf-8") as f:
            inhoud = f.read()
        delen.append(f"\n\n####### laag: {naam} #######\n\n{inhoud.rstrip()}\n")
    return "\n".join(delen)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true",
                   help="niets schrijven; falen als de bundel afwijkt van de lagen")
    args = p.parse_args()

    bestanden = lagen()
    print("lagen:")
    for naam, _ in bestanden:
        print(f"  - {naam}")

    for fout in controleer_aanbieder_lagen(bestanden):
        print(f"\nFOUT: shacl:minCount in een aanbieder-laag: {fout}", file=sys.stderr)
        print("Een aanbieder-laag mag nooit aanwezigheid eisen - zie de docstring.",
              file=sys.stderr)
        return 1
    for fout in controleer_prefixen(bestanden):
        print(f"\nFOUT: {fout}", file=sys.stderr)
        return 1

    inhoud = bouw(bestanden)

    if args.check:
        if not os.path.exists(UIT):
            print(f"\nFOUT: {os.path.relpath(UIT, REPO)} bestaat niet.", file=sys.stderr)
            return 1
        huidig = open(UIT, encoding="utf-8").read()
        # de builddatum in de kop mag verschillen
        schoon = lambda t: re.sub(r"# Gebouwd op \d{4}-\d{2}-\d{2}", "", t)
        if schoon(huidig) != schoon(inhoud):
            print(f"\nFOUT: {os.path.relpath(UIT, REPO)} loopt achter op de lagen. "
                  "Draai validation/build_bundle.py en commit het resultaat.", file=sys.stderr)
            return 1
        print("\nbundel is actueel.")
        return 0

    os.makedirs(os.path.dirname(UIT), exist_ok=True)
    with open(UIT, "w", encoding="utf-8") as f:
        f.write(inhoud)

    # controleren dat het resultaat parset en niets kwijtraakt
    try:
        from rdflib import Graph, Namespace, RDF
        SH = Namespace("http://www.w3.org/ns/shacl#")
        g = Graph()
        g.parse(UIT, format="turtle")
        som = 0
        for _, pad in bestanden:
            los = Graph()
            los.parse(pad, format="turtle")
            som += len(los)
        shapes = len(set(g.subjects(RDF.type, SH.NodeShape)))
        props = len(set(g.subjects(RDF.type, SH.PropertyShape)))
        print(f"\ngeschreven: {os.path.relpath(UIT, REPO)}")
        print(f"  {len(g)} triples, {shapes} NodeShapes, {props} benoemde PropertyShapes")
        if len(g) != som:
            print(f"  LET OP: losse lagen samen {som} triples; verschil {som - len(g)} "
                  "(identieke triples in meerdere lagen worden samengevoegd)")
    except ImportError:
        print("\n(rdflib niet beschikbaar: parse-controle overgeslagen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
