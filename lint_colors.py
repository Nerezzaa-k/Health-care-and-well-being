"""
Lint tool for checking that no color literals exist outside static/tokens.css.
Allowed color values: var(--...), transparent, currentColor, inherit, none.
Disallowed: hex codes (#...), rgb/rgba, hsl/hsla, and named color values.
"""
import os
import re
import sys

HEX_RE = re.compile(r'#(?:[0-9a-fA-F]{3,4}){1,2}\b')
RGB_RE = re.compile(r'\b(?:rgb|hsl)a?\([^\)]+\)', re.IGNORECASE)

# Detect named colors when used in CSS property values, inline styles, or SVG attributes
NAMED_COLORS = [
    'white', 'black', 'red', 'green', 'blue', 'purple', 'yellow', 
    'orange', 'gray', 'grey', 'teal', 'navy', 'crimson', 'cyan', 'magenta'
]
NAMED_RE = re.compile(
    r'(?:(?:color|background|background-color|border-color|fill|stroke|outline-color|box-shadow)\s*:\s*|fill=["\']|stroke=["\'])(' + 
    '|'.join(NAMED_COLORS) + r')\b', 
    re.IGNORECASE
)

# Files to scan
LINT_FILES = [
    os.path.join('static', 'index.html'),
    os.path.join('static', 'styles.css'),
    os.path.join('static', 'app.js'),
]

def scan_file(filepath):
    if not os.path.exists(filepath):
        return []
    violations = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for line_no, line in enumerate(lines, 1):
        # Ignore comments if purely comment
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            continue
            
        # Check hex
        for match in HEX_RE.finditer(line):
            # Check if this is an ID selector (e.g. #appScreen, #secScorecard, #toastIcon)
            start_pos = match.start()
            prefix = line[max(0, start_pos - 15):start_pos]
            val = match.group(0)
            # If line contains getElementById('...') or id="..." or querySelector('#...')
            # then #name is not a color unless it's a 3,4,6,8-digit hex inside style/css
            if 'id=' in prefix or 'getElementById' in line or 'querySelector' in line:
                # likely an ID selector if followed by non-hex or in quotes as element ID
                if not re.search(r'(?:color|background|fill|stroke|border|box-shadow|style|#|\'|\")', prefix):
                    continue
            violations.append((filepath, line_no, f"Hex color literal: {val}", line.strip()[:80]))
            
        # Check rgb/hsl
        for match in RGB_RE.finditer(line):
            val = match.group(0)
            violations.append((filepath, line_no, f"RGB/HSL literal: {val}", line.strip()[:80]))
            
        # Check named colors
        for match in NAMED_RE.finditer(line):
            val = match.group(1)
            violations.append((filepath, line_no, f"Named color literal: {val}", line.strip()[:80]))
            
    return violations

def main():
    total_violations = []
    print("=== LINT:COLORS SCANNING ===")
    for f in LINT_FILES:
        viols = scan_file(f)
        total_violations.extend(viols)
        print(f"{f}: {len(viols)} color literal violations")
        
    print(f"Total color literals found outside tokens file: {len(total_violations)}")
    if total_violations:
        print("\nSample violations:")
        for fpath, lno, reason, text in total_violations[:15]:
            print(f"  {fpath}:{lno}: {reason} in -> {text}")
        if len(total_violations) > 15:
            print(f"  ... and {len(total_violations) - 15} more.")
        return len(total_violations)
    else:
        print("\n[ PASS ] lint:colors: Zero color literals found outside tokens file!")
        return 0

if __name__ == '__main__':
    code = main()
    sys.exit(0 if code == 0 else 1)
