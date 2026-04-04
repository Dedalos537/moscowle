with open("app/templates/admin/deudores.html", "r") as f:
    text = f.read()

# Fix 1: The closed div
text = text.replace('<div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 animate-slide-in"></div>', '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 animate-slide-in">')

with open("app/templates/admin/deudores.html", "w") as f:
    f.write(text)
