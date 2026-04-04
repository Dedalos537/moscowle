with open("app/templates/admin/deudores.html", "r") as f:
    text = f.read()

text = text.replace("{% endblock %}\n<div id=\"marcarPagadoModal\"", "<div id=\"marcarPagadoModal\"")

if text.endswith("</script>"):
    text += "\n{% endblock %}\n"
elif text.endswith("</script>\n"):
    text += "{% endblock %}\n"

with open("app/templates/admin/deudores.html", "w") as f:
    f.write(text)
