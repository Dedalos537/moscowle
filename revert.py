with open("app/templates/admin/deudores.html", "r") as f:
    text = f.read()

text = text.replace('<div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 animate-slide-in">', '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 animate-slide-in"></div>')

with open("app/templates/admin/deudores.html", "w") as f:
    f.write(text)
