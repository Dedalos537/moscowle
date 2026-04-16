import re

with open('app/templates/admin/payment_history.html', 'r') as f:
    content = f.read()

# Replace the "Recibo PDF" anchor tag to call JS instead.
old_link = """<a href="{{ url_for('admin.download_receipt', payment_id=p.id) }}" target="_blank" class="text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-1">
                                <i class="fas fa-file-pdf text-red-500"></i> Recibo PDF
                            </a>"""

new_link = """<a href="#" onclick="openGenerateReceiptModal('{{ p.id }}', '{{ p.patient.guardian_name or p.patient.username or '' }}', '{{ getattr(p.patient, \'document_number\', \'\') }}', '{{ p.notes or '' }}'); return false;" class="text-primary hover:text-green-700 font-bold flex items-center gap-1">
                                <i class="fas fa-file-pdf text-red-500"></i> Recibo PDF
                            </a>"""

content = content.replace(old_link, new_link)

# Add the Modal code to the end, right before </body> or inside a script block? 
# Usually right before closing block content
modal_code = """
<!-- Modal Generate Receipt -->
<div id="generateReceiptModal" class="fixed inset-0 bg-black bg-opacity-50 hidden z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-soft shadow-soft w-full max-w-md p-6 relative">
        <button onclick="closeGenerateReceiptModal()" class="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
            <i class="fas fa-times"></i>
        </button>
        <h3 class="text-xl font-bold text-charcoal mb-4">Generar Recibo</h3>
        
        <div id="missing_receipt_data_warning" class="hidden mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-800">
            <i class="fas fa-exclamation-triangle"></i> Faltan datos obligatorios. Complétalos para generar el PDF.
        </div>
        <p class="text-sm text-gray-500 mb-4">Verifica los datos que aparecerán en el recibo. Modifícalos si es necesario.</p>
        
        <!-- target blank so it opens download in new tab automatically -->
        <form id="receiptForm" method="POST" action="" target="_blank" onsubmit="setTimeout(closeGenerateReceiptModal, 500);">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            
            <div class="mb-4">
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Nombre o Razón Social (Apoderado)</label>
                <input type="text" name="guardian_name" id="receipt_guardian_name" class="w-full px-3 py-2 border rounded-soft" required>
            </div>
            
            <div class="mb-4">
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">DNI o Documento</label>
                <input type="text" name="document_number" id="receipt_document_number" class="w-full px-3 py-2 border rounded-soft" required>
            </div>
            
            <div class="mb-4">
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Concepto de Pago (Opcional)</label>
                <input type="text" name="concept" id="receipt_concept" class="w-full px-3 py-2 border rounded-soft" placeholder="Ej: Servicios de Terapia">
            </div>

            <div class="flex gap-2 mt-6">
                <button type="button" onclick="closeGenerateReceiptModal()" class="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-soft font-medium hover:bg-gray-300">
                    Cancelar
                </button>
                <button type="submit" class="flex-1 px-4 py-2 bg-primary text-white rounded-soft font-medium flex items-center justify-center gap-2">
                    <i class="fas fa-file-pdf"></i> Generar Archivo
                </button>
            </div>
        </form>
    </div>
</div>

<script>
function openGenerateReceiptModal(paymentId, guardianName, docNumber, concept) {
    document.getElementById('receipt_guardian_name').value = guardianName || '';
    document.getElementById('receipt_document_number').value = docNumber || '';
    document.getElementById('receipt_concept').value = concept || '';
    
    if (!guardianName || !docNumber) {
        document.getElementById('missing_receipt_data_warning').classList.remove('hidden');
    } else {
        document.getElementById('missing_receipt_data_warning').classList.add('hidden');
    }
    
    const form = document.getElementById('receiptForm');
    form.action = `/admin/payments/${paymentId}/receipt`;
    
    document.getElementById('generateReceiptModal').classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

function closeGenerateReceiptModal() {
    document.getElementById('generateReceiptModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
}
</script>
"""

# Instead of appending globally, let's inject it before {% endblock %}
if "<!-- Modal Generate Receipt -->" not in content:
    content = content.replace("{% endblock %}", modal_code + "\n{% endblock %}")

with open('app/templates/admin/payment_history.html', 'w') as f:
    f.write(content)
