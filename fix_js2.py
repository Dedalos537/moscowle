with open("app/templates/admin/deudores.html", "r") as f:
    text = f.read()

text = text.replace("document.addEventListener('DOMContentLoaded', () => {", "console.log('Script loaded'); document.addEventListener('DOMContentLoaded', () => { console.log('DOM loaded');")

with open("app/templates/admin/deudores.html", "w") as f:
    f.write(text)
