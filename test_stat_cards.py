import re
import os

filepath = 'app/templates/admin/deudores.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Let's see what is inside deudores.html
print("Deudores.html size:", len(content))
if 'stat-card' in content:
    print("Found stat-card in Deudores!")
    
