
import os

def search_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Search for url_for('profile') or url_for("profile")
            # Be flexible with spaces
            if "url_for" in content and "profile" in content:
                # Check specifically for the pattern
                import re
                # Pattern: url_for \s* ( \s* ['"] profile ['"] \s* )
                pattern = re.compile(r"url_for\s*\(\s*['\"]profile['\"]\s*\)")
                matches = pattern.findall(content)
                if matches:
                    print(f"Found in {filepath}")
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if pattern.search(line):
                            print(f"Line {i+1}: {line.strip()}")
    except Exception as e:
        print(f"Could not read {filepath}: {e}")

print("Searching for incorrect url_for('profile')...")
for root, dirs, files in os.walk('app/templates'):
    for file in files:
        if file.endswith('.html'):
            search_in_file(os.path.join(root, file))
