import re

filepath = 'app/templates/admin/payments.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the Comprobante cell
old_cell = """                <td class="px-6 py-4 text-sm text-gray-500">
                    {% if pay.receipt_image_path %}
                        <a href="{{ url_for('uploads.protected_file', filename=pay.receipt_image_path) }}" target="_blank" class="text-blue-500 hover:underline text-xs flex items-center gap-1">
                            <i class="fas fa-paperclip"></i> Ver Voucher
                        </a>
                    {% else %}
                        <span class="text-gray-300 text-xs">-</span>
                    {% endif %}
                </td>"""

new_cell = """                <td class="px-6 py-4 text-sm text-gray-500 flex flex-col gap-2">
                    <a href="{{ url_for('admin.download_receipt', payment_id=pay.id) }}" target="_blank" class="text-indigo-600 hover:text-indigo-800 text-xs font-bold flex items-center gap-1">
                        <i class="fas fa-file-pdf text-red-500"></i> Recibo Digital
                    </a>
                    {% if pay.receipt_image_path %}
                        <a href="{{ url_for('uploads.protected_file', filename=pay.receipt_image_path) }}" target="_blank" class="text-blue-500 hover:underline text-xs flex items-center gap-1">
                            <i class="fas fa-paperclip"></i> Ver Voucher
                        </a>
                    {% endif %}
                </td>"""

if old_cell in content:
    content = content.replace(old_cell, new_cell)

# Update header label slightly
content = content.replace('<th class="px-6 py-4 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Comprobante</th>', '<th class="px-6 py-4 text-left text-xs font-bold text-gray-400 uppercase tracking-wider">Documentos</th>')

# I also should update `payment_history.html` if it exists.
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated payments.html")
