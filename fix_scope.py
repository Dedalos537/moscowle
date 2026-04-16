import re
with open('app/services/receipt_generator.py', 'r') as f:
    text = f.read()

text = text.replace("    try:\n        logo_path = os.path.join(", "    logo_path = ''\n    try:\n        logo_path = os.path.join(")

with open('app/services/receipt_generator.py', 'w') as f:
    f.write(text)
print("scope fixed")
