#!/usr/bin/env python3
"""
Generate basic source maps for JavaScript files to enable better debugging
"""
import os
import json
from pathlib import Path

def create_source_map(js_file_path):
    """Create a basic source map for a JavaScript file"""
    js_path = Path(js_file_path)
    if not js_path.exists():
        return None
    
    # Read the JavaScript file
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Create a basic source map
    source_map = {
        "version": 3,
        "file": js_path.name,
        "sourceRoot": "",
        "sources": [js_path.name],
        "sourcesContent": [content],
        "names": [],
        "mappings": ""
    }
    
    # Simple line-by-line mapping (AAAA,AAAA,...)
    mappings = []
    for i, line in enumerate(lines):
        if line.strip():  # Only map non-empty lines
            mappings.append("AAAA")
        else:
            mappings.append("")
    
    source_map["mappings"] = ";".join(mappings)
    
    # Write source map file
    map_path = js_path.with_suffix('.js.map')
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(source_map, f, indent=2)
    
    # Add source map reference to JS file if not already present
    if '//# sourceMappingURL=' not in content:
        with open(js_path, 'a', encoding='utf-8') as f:
            f.write(f'\n//# sourceMappingURL={map_path.name}\n')
    
    return map_path

def main():
    """Generate source maps for all JavaScript files in the static directory"""
    static_dir = Path(__file__).parent.parent / 'static'
    js_files = []
    
    # Find all JavaScript files
    for js_file in static_dir.rglob('*.js'):
        if not js_file.name.endswith('.map'):  # Skip existing map files
            js_files.append(js_file)
    
    print(f"Found {len(js_files)} JavaScript files")
    
    created_maps = []
    for js_file in js_files:
        try:
            map_path = create_source_map(js_file)
            if map_path:
                created_maps.append(map_path)
                print(f"✓ Created source map: {map_path}")
        except Exception as e:
            print(f"✗ Failed to create source map for {js_file}: {e}")
    
    print(f"\nCreated {len(created_maps)} source maps")
    return created_maps

if __name__ == '__main__':
    main()

