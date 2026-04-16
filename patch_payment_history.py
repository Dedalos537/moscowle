import re

filepath = 'app/templates/admin/payment_history.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_td = """                        <td class="px-6 py-4 text-sm">
                            {% if p.receipt_image_path %}
                            <button onclick="openReceiptModal('{{ p.receipt_image_path }}')" class="text-primary hover:text-green-700 flex items-center gap-1 font-medium">
                                <i class="fas fa-file-image"></i> Ver Voucher
                            </button>
                            {% else %}
                            <span class="text-gray-300 italic">Sin archivo</span>
                            {% endif %}
                        </td>"""

new_td = """                        <td class="px-6 py-4 text-sm flex flex-col gap-2">
                            <a href="{{ url_for('admin.download_receipt', payment_id=p.id) }}" target="_blank" class="text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-1">
                                <i class="fas fa-file-pdf text-red-500"></i> Recibo PDF
                            </a>
                            {% if p.receipt_image_path %}
                            <button onclick="openReceiptModal('{{ p.receipt_image_path }}')" class="text-primary hover:text-green-700 flex items-center gap-1 font-medium mt-1">
                                <i class="fas fa-file-image text-blue-500"></i> Ver Voucher
                            </button>
                            {% endif %}
                        </td>"""

content = content.replace(old_td, new_td)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated payment_history.html")
