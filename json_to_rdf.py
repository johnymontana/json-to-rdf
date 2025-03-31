#!/usr/bin/env python3
"""
JSON to RDF Converter
Converts JSON files to RDF formats compatible with Dgraph import
"""

import json
import sys
import os
import hashlib
import argparse
from urllib.parse import quote
from collections import defaultdict

def determine_datatype(value):
    """Determine the appropriate XSD datatype for a JSON value"""
    if isinstance(value, bool):
        return "xs:boolean"
    elif isinstance(value, int):
        return "xs:int"
    elif isinstance(value, float):
        return "xs:float"
    elif value is None:
        return None  # Will be handled as a special case
    else:
        return "xs:string"

def generate_uid(text):
    """Generate a consistent UID for a node based on its text representation"""
    # Create a hash of the text to generate a consistent UID
    hash_obj = hashlib.md5(text.encode())
    # Return first 16 chars of the hexdigest
    return hash_obj.hexdigest()[:16]

def json_to_dgraph_rdf(json_data, base_prefix="node"):
    """
    Convert JSON data to RDF in Dgraph format
    
    Args:
        json_data: The parsed JSON data
        base_prefix: The prefix to use for blank node identifiers
        
    Returns:
        A list of RDF triples in Dgraph format
    """
    triples = []
    
    # Process the JSON recursively
    def process_json(data, parent_node=None, parent_key=None, parent_path=""):
        if parent_node is None:
            # Root object
            current_path = f"{base_prefix}_root"
            current_node = f"_:{current_path}"
            triples.append(f"{current_node} <dgraph.type> \"Object\" .")
        else:
            # Create a unique node identifier
            safe_key = quote(str(parent_key))
            current_path = f"{parent_path}_{safe_key}" if parent_path else f"{base_prefix}_{safe_key}"
            current_node = f"_:{current_path}"
            
        if isinstance(data, dict):
            # This is a JSON object
            if parent_node is not None:  # Not the root
                triples.append(f"{current_node} <dgraph.type> \"Object\" .")
                triples.append(f"{parent_node} <{parent_key}> {current_node} .")
            
            # Process all key-value pairs
            for key, value in data.items():
                process_json(value, current_node, key)
                
        elif isinstance(data, list):
            # This is a JSON array
            if parent_node is not None:  # Not the root
                triples.append(f"{current_node} <dgraph.type> \"Array\" .")
                triples.append(f"{parent_node} <{parent_key}> {current_node} .")
            
            # Process all array items with their index as key
            for i, item in enumerate(data):
                process_json(item, current_node, str(i), current_path)
                
        else:
            # This is a primitive value
            if data is None:
                # Handle null values
                triples.append(f"{parent_node} <{parent_key}> \"null\" .")
            else:
                datatype = determine_datatype(data)
                if datatype:
                    # Format the value according to its type
                    if isinstance(data, bool):
                        value_str = str(data).lower()
                    else:
                        value_str = str(data)
                    
                    # Add the triple with datatype
                    triples.append(f"{parent_node} <{parent_key}> \"{value_str}\"^^<{datatype}> .")
                else:
                    # String without datatype
                    triples.append(f"{parent_node} <{parent_key}> \"{data}\" .")
    
    # Start processing from the root
    process_json(json_data, None, None, "")
    return triples


def generate_dql_schema(triples):
    """
    Generate a DQL schema based on the RDF triples
    
    Args:
        triples: List of RDF triples in Dgraph format
        
    Returns:
        A string containing the DQL schema
    """
    # Track predicates and their types
    predicates = defaultdict(set)
    
    # Analyze triples to determine predicate types
    for triple in triples:
        parts = triple.split()
        if len(parts) >= 4 and parts[1].startswith('<') and parts[1].endswith('>'):
            predicate = parts[1][1:-1]  # Remove < and >
            
            # Skip dgraph.type predicate
            if predicate == "dgraph.type":
                continue
                
            # Check if this is a node reference (object starts with _:)
            if parts[2].startswith('_:'):
                predicates[predicate].add('uid')
            else:
                # Extract the datatype if present
                value_part = ' '.join(parts[2:])
                if '^^<xs:' in value_part:
                    datatype = value_part.split('^^<xs:')[1].split('>')[0]
                    predicates[predicate].add(datatype)
                else:
                    # Default to string for literals without explicit datatype
                    predicates[predicate].add('string')
    
    # Generate the schema
    schema_lines = []
    schema_lines.append('# DQL Schema generated from RDF data')
    schema_lines.append('# Define types for each predicate')
    
    for predicate, types in sorted(predicates.items()):
        # Convert types to DQL type
        dql_types = []
        for t in types:
            if t == 'uid':
                dql_types.append('uid')
            elif t == 'int':
                dql_types.append('int')
            elif t == 'float':
                dql_types.append('float')
            elif t == 'boolean':
                dql_types.append('bool')
            else:
                dql_types.append('string')
        
        # Join multiple types with |
        type_str = ' | '.join(dql_types)
        schema_lines.append(f'{predicate}: {type_str} .')
    
    return '\n'.join(schema_lines)

def main():
    """Main function to handle CLI arguments and process files"""
    parser = argparse.ArgumentParser(description='Convert JSON files to RDF formats for Dgraph import')
    parser.add_argument('input_file', help='Path to the input JSON file')
    parser.add_argument('output_file', help='Path to the output RDF file')
    parser.add_argument('--base-prefix', default='node',
                        help='Base prefix for blank node identifiers (default: node)')
    parser.add_argument('--schema-file', 
                        help='Path to output DQL schema file (optional)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.isfile(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist", file=sys.stderr)
        return 1
    
    try:
        # Load JSON data
        with open(args.input_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Convert to Dgraph RDF
        triples = json_to_dgraph_rdf(json_data, args.base_prefix)
        
        # Write to output file
        with open(args.output_file, 'w', encoding='utf-8') as f:
            for triple in triples:
                f.write(f"{triple}\n")
        
        print(f"Successfully converted '{args.input_file}' to '{args.output_file}' in Dgraph RDF format")
        print(f"Generated {len(triples)} RDF statements")
        
        # Generate and write DQL schema if requested
        if args.schema_file:
            schema = generate_dql_schema(triples)
            with open(args.schema_file, 'w', encoding='utf-8') as f:
                f.write(schema)
            print(f"Generated DQL schema and wrote to '{args.schema_file}'")
            
        return 0
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{args.input_file}': {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
