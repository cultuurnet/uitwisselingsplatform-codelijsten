from rdflib import Graph
from pyshacl import validate
import os

schemes_dir = './conceptschemes'
ontology_dir = './ontology'

def validate_shape(graph):
    return validate(data_graph=graph, shacl_graph="shacl_codelists.ttl")
    
def validate_turtle_with_shacl(file_path):
    """Validate a turtle file with SHACL shapes (for concept schemes)."""
    try:
        g = Graph()
        g.parse(file_path, format="turtle")
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return False
    (is_valid, _, failure_reason) = validate_shape(g)
    if is_valid:
        return True
    else:
        print(f"Error validating shape {file_path}: {failure_reason}")
        return False

def validate_turtle_syntax_only(file_path):
    """Validate a turtle file syntax only (for ontology files)."""
    try:
        g = Graph()
        g.parse(file_path, format="turtle")
        print(f"✓ Syntax validation passed for {file_path}")
        return True
    except Exception as e:
        print(f"Error validating syntax {file_path}: {e}")
        return False

# Track validation results
all_valid = True

# Validate concept schemes with SHACL
if os.path.exists(schemes_dir):
    print("### Validating concept schemes ###")
    for filename_codelist in os.listdir(schemes_dir):
        if filename_codelist.endswith('.ttl'):
            print(f"### Parsing file {filename_codelist} ###")
            file = os.path.join(schemes_dir, filename_codelist)
            if not validate_turtle_with_shacl(file):
                all_valid = False
else:
    print(f"Warning: {schemes_dir} directory not found")

# Validate ontology files with syntax-only check
if os.path.exists(ontology_dir):
    print("\n### Validating ontology files ###")
    for filename_ontology in os.listdir(ontology_dir):
        if filename_ontology.endswith('.ttl'):
            print(f"### Parsing file {filename_ontology} ###")
            file = os.path.join(ontology_dir, filename_ontology)
            if not validate_turtle_syntax_only(file):
                all_valid = False
else:
    print(f"Warning: {ontology_dir} directory not found")

# Exit with appropriate code
if not all_valid:
    print("\n❌ Validation failed. Please fix the errors above.")
    exit(1)
else:
    print("\n✓ All validations passed.")
    exit(0)