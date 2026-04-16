import re

with open('app/templates/admin/deudores.html', 'r') as f:
    content = f.read()

old_code = """
        // Fetch billing info via API (safe)
        safeApiFetch(`/admin/api/payment-info/${id}`).then(resp=>{
            if(resp.success && resp.data){
                if(resp.data.suggested_date) document.getElementById('payment_next_date').value = resp.data.suggested_date;
                if(resp.data.absences && resp.data.absences>0){ const hint = document.getElementById('absences_hint'); hint.textContent = `⚠️ ${resp.data.absences} faltas desde el último pago.`; hint.classList.remove('hidden'); }
            }
        }).catch(()=>{});
"""

new_code = """
        // Fetch billing info via API (safe)
        safeApiFetch(`/admin/api/payment-info/${id}`).then(resp=>{
            if(resp.success && resp.data){
                if(resp.data.suggested_date) document.getElementById('payment_next_date').value = resp.data.suggested_date;
                if(resp.data.absences && resp.data.absences>0){ const hint = document.getElementById('absences_hint'); hint.textContent = `⚠️ ${resp.data.absences} faltas desde el último pago.`; hint.classList.remove('hidden'); }
                
                // Handle missing receipt data
                const docInput = document.getElementById('input_document_number');
                const guardInput = document.getElementById('input_guardian_name');
                const docFg = document.getElementById('fg_document_number');
                const guardFg = document.getElementById('fg_guardian_name');
                const warning = document.getElementById('missing_data_warning');
                
                if(docInput) docInput.value = resp.data.document_number || '';
                if(guardInput) guardInput.value = resp.data.guardian_name || '';
                
                let missing = false;
                if (!resp.data.document_number) {
                    if(docFg) docFg.classList.remove('hidden');
                    missing = true;
                } else {
                    if(docFg) docFg.classList.add('hidden');
                }
                
                // Usually check age, but for MVP if it's missing just ask for DNI first
                if (!resp.data.guardian_name) {
                    if(guardFg) guardFg.classList.remove('hidden');
                } else {
                    if(guardFg) guardFg.classList.add('hidden');
                }
                
                if (missing) {
                    if(warning) warning.classList.remove('hidden');
                    if(docInput) docInput.required = true;
                } else {
                    if(warning) warning.classList.add('hidden');
                    if(docInput) docInput.required = false;
                }
            }
        }).catch(()=>{});
"""

content = content.replace(old_code, new_code)

with open('app/templates/admin/deudores.html', 'w') as f:
    f.write(content)
