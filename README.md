# JSON to RDF Converter

A Python utility for converting JSON files to RDF N-Quad format.

## Features

- Parse JSON files and convert them to RDF triples
- Output RDF data in N-Quad format
- Preserve JSON structure in the resulting RDF graph

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

```bash
python json_to_rdf.py input.json output.nq
```

Where:
- `input.json` is the path to your JSON file
- `output.nq` is the path where the N-Quad RDF file will be saved

## Example

```bash
python json_to_rdf.py examples/sample.json examples/sample.nq
```

## Requirements

- Python 3.6+
- rdflib 6.3.2+
