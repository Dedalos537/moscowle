import re

with open('app/templates/admin/payment_history.html', 'r') as f:
    text = f.read()

import re

# We want to replace the <a href="{{ url_for('admin.download_receipt', payment_id=p.id) }}" ...>
# with the onclick version.

text = re.sub(
    r'<a href="\{\{ url_for\(\'admin.download_receipt\', payment_id=p.id\) \}\}"[^>]*>',
    r'''<a href="#" onclick="openGenerateReceiptModal('{{ p.id }}', '{{ p.patient.guardian_name or p.patient.username or \'\' }}', '{{ p.patient.document_number or \'\' }}', '{{ p.notes or \'\' }}'); return false;" class="text-primary hover:text-green-700 font-bold flex items-center gap-1 mb-1">''',
    text,
    flags=re.DOTALL
)

with open('app/templates/admin/payment_history.html', 'w') as f:
    f.write(text)
print("Link replaced.")
