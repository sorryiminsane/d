#!/usr/bin/env python3
import os
import re

# Read the base64 data
with open('coinbase_base64.txt', 'r') as f:
    base64_data = f.read().strip()

# Read the HTML template
template_path = 'templates/coinbase/emp.html'
with open(template_path, 'r') as f:
    html_content = f.read()

# Replace the CID image reference with base64 data URI
pattern = r'<img src="cid:logo" alt="Coinbase" width="160" style="display: block; margin: 0 auto; max-width: 160px; height: auto;"/>'
replacement = f'<img src="data:image/png;base64,{base64_data}" alt="Coinbase" width="160" style="display: block; margin: 0 auto; max-width: 160px; height: auto;"/>'

updated_html = html_content.replace(pattern, replacement)

# Write the updated HTML back to the file
with open(template_path, 'w') as f:
    f.write(updated_html)

print(f"Updated {template_path} with base64 image data")
