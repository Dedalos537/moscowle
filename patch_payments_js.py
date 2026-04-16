import re

with open('app/templates/admin/payments.html', 'r') as f:
    content = f.read()

old_code = """
    // Fetch suggested data
    fetch(`/admin/api/payment-info/${patient_id}`)
        .then(r=>r.json())
        .then(data=>{
            const nextDateInput = document.getElementById('payment_next_date');
            
            if(data.suggested_date) {
                nextDateInput.value = data.suggested_date;
                document.getElementById('recalc_date').textContent = data.suggested_date;
            }
            if(data.suggested_sessions) document.getElementById('recalc_sessions').textContent = data.suggested_sessions;
            
            if(data.recovery_msg) {
                document.getElementById('recalc_recovery').textContent = " - " + data.recovery_msg;
            } else {
                document.getElementById('recalc_recovery').textContent = "";
            }
            
            if(data.current_plan) {
                document.getElementById('recalc_plan').textContent = data.current_plan;
            }
            
            document.getElementById('recalc_alert').classList.remove('hidden');
        }).catch(err => console.error("Error fetching recommendation", err));
"""

new_code = """
    // Fetch suggested data
    fetch(`/admin/api/payment-info/${patient_id}`)
        .then(r=>r.json())
        .then(data=>{
            const nextDateInput = document.getElementById('payment_next_date');
            
            if(data.suggested_date) {
                nextDateInput.value = data.suggested_date;
                document.getElementById('recalc_date').textContent = data.suggested_date;
            }
            if(data.suggested_sessions) document.getElementById('recalc_sessions').textContent = data.suggested_sessions;
            
            if(data.recovery_msg) {
                document.getElementById('recalc_recovery').textContent = " - " + data.recovery_msg;
            } else {
                document.getElementById('recalc_recovery').textContent = "";
            }
            
            if(data.current_plan) {
                document.getElementById('recalc_plan').textContent = data.current_plan;
            }
            
            // DNI fields
            const docInput = document.getElementById('input_document_number');
            const guardInput = document.getElementById('input_guardian_name');
            const docFg = document.getElementById('fg_document_number');
            const guardFg = document.getElementById('fg_guardian_name');
            const warning = document.getElementById('missing_data_warning');
            
            let missing = false;
            if(!data.document_number) {
                if(docFg) docFg.classList.remove('hidden');
                if(docInput) docInput.required = true;
                missing = true;
            } else {
                if(docFg) docFg.classList.add('hidden');
                if(docInput) docInput.required = false;
            }
            
            if(!data.guardian_name) {
                if(guardFg) guardFg.classList.remove('hidden');
            } else {
                if(guardFg) guardFg.classList.add('hidden');
            }
            
            if(missing) {
                if(warning) warning.classList.remove('hidden');
            } else {
                if(warning) warning.classList.add('hidden');
            }
            
            document.getElementById('recalc_alert').classList.remove('hidden');
        }).catch(err => console.error("Error fetching recommendation", err));
"""

content = content.replace(old_code, new_code)

with open('app/templates/admin/payments.html', 'w') as f:
    f.write(content)
