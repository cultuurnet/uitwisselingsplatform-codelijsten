from rdflib import Graph
from pyshacl import validate
import os

schemes_dir = './conceptschemes'

def validate_shape(graph):
    return validate(data_graph=graph, shacl_graph="shacl_codelists.ttl")
    
def validate_turtle(file_path):
    try:
        g = Graph()
        g.parse(file_path, format="turtle")
    except Exception as e:
        print(f"Error validating {file_path}: {e}")
        return False
    (is_valid, _, failure_reason)=  validate_shape(g)
    if is_valid:
        return True
    else:
        print(f"Error validating shape {file_path}: {failure_reason}")
        return False
      
for filename_codelist in os.listdir(schemes_dir):
  print("### Parsing file ", filename_codelist, "###")
  file = os.path.join(schemes_dir, filename_codelist)
  validate_turtle(file)