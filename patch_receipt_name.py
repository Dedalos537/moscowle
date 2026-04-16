import re

filepath = 'app/services/receipt_generator.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("client_name = patient.guardian_name or patient.name", "client_name = patient.guardian_name or patient.username")
content = content.replace("['Paciente Asignado:', patient.name]", "['Paciente Asignado:', patient.username]")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated receipt_generator.py")
