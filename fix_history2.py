import re

with open('app/templates/admin/payment_history.html', 'r') as f:
    text = f.read()

# Locate the broken anchor line exactly
old_anchor = """<a href="#" onclick="openGenerateReceiptModal(\'{{ p.id }}\', \'{{ (p.patient.guardian_name or p.patient.username or \'\')|replace(\"\'\", \"\\\\\'\") }}\', \'{{ (p.patient.document_number or \'\')|replace(\"\'\", \"\\\\\'\") }}\', \'{{ (p.notes or \'\')|replace(\"\'\", \"\\\\\'\") }}\'); return false;" class="text-primary hover:text-green-700 font-bold flex items-center gap-1">"""

new_anchor = """<a href="#" 
    data-payment-id="{{ p.id }}"
    data-guardian="{{ p.patient.guardian_name or p.patient.username or '' }}"
    data-doc="{{ p.patient.document_number or '' }}"
    data-concept="{{ p.notes or '' }}"
    onclick="var el=this; openGenerateReceiptModal(el.getAttribute('data-payment-id'), el.getAttribute('data-guardian'), el.getAttribute('data-doc'), el.getAttribute('data-concept')); return false;" 
    class="text-primary hover:text-green-700 font-bold flex items-center gap-1">"""

if old_anchor in text:
    print("Found exact old string!")
    text = text.replace(old_anchor, new_anchor)
else:
    print("Exact old string not found, falling back to regex")
    text = re.sub(
        r'<a href="#" onclick="openGenerateReceiptModal.*return false;" class="text-primary hover:text-green-700 font-bold flex items-center gap-1">',
        new_anchor,
        text
    )

with open('app/templates/admin/payment_history.html', 'w') as f:
    f.write(text)

print("Replaced!")
