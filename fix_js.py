with open("app/templates/admin/deudores.html", "r") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if "let currentPaymentId = null;" in line and i > 500:
        continue # Skip the duplicate declaration
    
    if 'document.querySelector("#marcarPagadoModal button.bg-blue-600")' in line:
        line = line.replace('button.bg-blue-600', 'button.bg-green-600')
        
    new_lines.append(line)

with open("app/templates/admin/deudores.html", "w") as f:
    f.writelines(new_lines)
