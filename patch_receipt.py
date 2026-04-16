import re

with open('app/services/receipt_generator.py', 'r') as f:
    content = f.read()

# Swap colors
content = content.replace("colors.HexColor('#1e40af')", "colors.HexColor('#65a30d')")

# Change address
content = content.replace("Av. Francisco Pizarro 635, Rimac - Lima", "Jr.Vicus 311, Piura")

with open('app/services/receipt_generator.py', 'w') as f:
    f.write(content)
