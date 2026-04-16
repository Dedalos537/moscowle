import re
with open('app/templates/admin/payment_history.html', 'r') as f:
    text = f.read()

# Instead of the broken replace, let's just replace the whole anchor back to a simpler one that just uses escape filter or doesn't have the broken syntax.
old_broken = r"""replace\("'", "\\\\'"\)"""
# First, just revert the template error part.
# Let's fix lines using regex.
import re

text = re.sub(
    r"""onclick="openGenerateReceiptModal\('\{\{ p.id \}\}', '\{\{ \(p.patient.guardian_name or p.patient.username or ''\)\|replace\("'", "\\\\'"\) \}\}', '\{\{ \(p.patient.document_number or ''\)\|replace\("'", "\\\\'"\) \}\}', '\{\{ \(p.notes or ''\)\|replace\("'", "\\\\'"\) \}\}'\); return false;\"""",
    r"""onclick="openGenerateReceiptModal('{{ p.id }}', '{{ (p.patient.guardian_name or p.patient.username or '') | replace( '\'', '\\\'' ) }}', '{{ (p.patient.document_number or '') | replace('\'', '\\\'') }}', '{{ (p.notes or '') | replace('\'', '\\\'') }}'); return false;\"""",
    text
)

# wait that's just as bad maybe.
# Better to do:
text = re.sub(r"onclick=.*openGenerateReceiptModal.*return false;\"",
r"""onclick="openGenerateReceiptModal('{{ p.id }}', '{{ (p.patient.guardian_name or p.patient.username or '') | replace('\x27', '\\\x27') }}', '{{ (p.patient.document_number or '') | replace('\x27', '\\\x27') }}', '{{ (p.notes or '') | replace('\x27', '\\\x27') }}'); return false;\"""", text)

with open('app/templates/admin/payment_history.html', 'w') as f:
    f.write(text)

