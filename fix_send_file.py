import re
with open('app/routes/admin_routes.py', 'r') as f:
    text = f.read()
if "send_file(" in text and "from flask import" in text and "send_file" in text.split("from flask import")[1].split("\n")[0]:
    print("Fixed!")
