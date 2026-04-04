with open("app/templates/admin/sessions.html", "r") as f:
    text = f.read()

text = text.replace("<style>", "{% block content %}\n<style>")
text = text.replace("</style>\n{% block content %}", "</style>")

with open("app/templates/admin/sessions.html", "w") as f:
    f.write(text)

