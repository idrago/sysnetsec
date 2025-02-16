#!/usr/bin/env python3

from pathlib import Path
import json
from datetime import datetime

def scan_system():
    """Scan system directories and save file listing to JSON"""
    system_paths = ['/etc', '/var/log', '/root']
    file_list = []

    for base_path in system_paths:
        path = Path(base_path)
        try:
            # Recursively get all files
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    file_info = {
                        'path': str(file_path),
                        'size': file_path.stat().st_size,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                    file_list.append(file_info)
        except Exception as e:
            continue

    # Save to file with timestamp
    output_file = f'/var/log/system_files.json'
    with open(output_file, 'w') as f:
        json.dump(file_list, f, indent=2)

if __name__ == "__main__":
    scan_system()
