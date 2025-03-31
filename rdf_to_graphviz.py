#!/usr/bin/env python3
"""
RDF to GraphViz Converter
Creates a GraphViz DOT file from an RDF file to visualize its schema
"""

import re
import sys
import os
import argparse

def parse_rdf_file(rdf_file):
    """
    Parse an RDF file and extract triples
    
    Args:
        rdf_file: Path to the RDF file
        
    Returns:
        List of tuples (subject, predicate, object)
    """
    triples = []
    
    with open(rdf_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # Parse the triple using regex
            # Format: _:node_root <predicate> "value"^^<datatype> .
            # or: _:node_root <predicate> _:node_other .
            match = re.match(r'(.*?)\s+<(.*?)>\s+(.*?)\s+\.', line)
            if match:
                subject = match.group(1).strip()
                predicate = match.group(2).strip()
                obj = match.group(3).strip()
                
                triples.append((subject, predicate, obj))
    
    return triples

def extract_schema(triples):
    """
    Extract schema information from RDF triples
    
    Args:
        triples: List of (subject, predicate, object) tuples
        
    Returns:
        Dictionary with schema information
    """
    nodes = {}
    edges = []
    
    # First pass: identify all nodes and their types
    for subject, predicate, obj in triples:
        if predicate == "dgraph.type":
            # Remove quotes from object
            node_type = obj.strip('"')
            nodes[subject] = {"type": node_type, "properties": set()}
    
    # Second pass: identify properties and relationships
    for subject, predicate, obj in triples:
        if predicate != "dgraph.type" and subject in nodes:
            if obj.startswith('_:'):  # This is a relationship to another node
                # Add edge between nodes
                edges.append((subject, predicate, obj))
            else:  # This is a property
                # Extract datatype if present
                datatype_match = re.search(r'\^\^<(.*?)>', obj)
                if datatype_match:
                    datatype = datatype_match.group(1)
                else:
                    datatype = "string"
                
                # Add property to node
                nodes[subject]["properties"].add((predicate, datatype))
    
    return {"nodes": nodes, "edges": edges}

def generate_graphviz(schema, output_file):
    """
    Generate a GraphViz DOT file from schema information
    
    Args:
        schema: Dictionary with schema information
        output_file: Path to the output DOT file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('digraph RDF_Schema {\n')
        f.write('  rankdir=LR;\n')
        f.write('  node [shape=record, style=filled, fillcolor=lightblue];\n')
        f.write('  edge [color=darkblue, fontcolor=darkblue];\n\n')
        
        # Write nodes with their properties
        for node_id, node_info in schema["nodes"].items():
            # Create a label with node type and properties
            label = f'{{<f0> {node_id}|<f1> Type: {node_info["type"]}'
            
            if node_info["properties"]:
                label += '|<f2> Properties:\\n'
                for prop, datatype in sorted(node_info["properties"]):
                    label += f'{prop}: {datatype}\\n'
            
            label += '}}'
            
            # Write node definition
            f.write(f'  "{node_id}" [label="{label}"];\n')
        
        f.write('\n')
        
        # Write edges
        for source, predicate, target in schema["edges"]:
            f.write(f'  "{source}" -> "{target}" [label="{predicate}"];\n')
        
        f.write('}\n')

def main():
    """Main function to handle CLI arguments and process files"""
    parser = argparse.ArgumentParser(description='Convert RDF file to GraphViz DOT file')
    parser.add_argument('input_file', help='Path to the input RDF file')
    parser.add_argument('output_file', help='Path to the output DOT file')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        return 1
    
    try:
        # Parse RDF file
        triples = parse_rdf_file(args.input_file)
        
        # Extract schema information
        schema = extract_schema(triples)
        
        # Generate GraphViz DOT file
        generate_graphviz(schema, args.output_file)
        
        print(f"Successfully generated GraphViz DOT file: {args.output_file}")
        print(f"To create a PNG image, run: dot -Tpng {args.output_file} -o {os.path.splitext(args.output_file)[0]}.png")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
