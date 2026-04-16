with open('app/templates/admin/payment_history.html', 'r') as f:
    text = f.read()

import re
old_onclick = r"""onclick="openGenerateReceiptModal\('\{\{ p.id \}\}', '\{\{ p.patient.guardian_name or p.patient.username or '' \}\}', '\{\{ p.patient.document_number or '' \}\}', '\{\{ p.notes or '' \}\}'\); return false;\""""
new_onclick = r"""onclick="openGenerateReceiptModal('{{ p.id }}', '{{ (p.patient.guardian_name or p.patient.username or '')|replace('\'', '\\\'') }}', '{{ (p.patient.document_number or '')|replace('\'', '\\\'') }}', '{{ (p.notes or '')|replace('\'', '\\\'') }}'); return false;\""""

text = re.sub(old_onclick, new_onclick, text)

with open('app/templates/admin/payment_history.html', 'w') as f:
    f.write(text)
print("Quotes patched")
