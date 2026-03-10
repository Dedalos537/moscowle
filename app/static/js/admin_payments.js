// Administration Payments Logic (Minified Logic for Production)
// Handles Modals, Filtering, Sorting and Chart interactions

let activeAgeFilter = null; // '0-30', '30-60', '60-90', '90+'
let activeChartFilter = false; 

function openRegisterPaymentModal(id, name, amount) {
    document.getElementById('payment_patient_id').value = id;
    document.getElementById('payment_patient_name').textContent = name;
    document.getElementById('payment_amount').value = amount;
    document.getElementById('payment_discount').value = ''; 
    document.getElementById('absences_hint').classList.add('hidden');
    
    // Fetch smart billing info
    fetch(`/admin/api/payment-info/${id}`)
        .then(response => response.json())
        .then(data => {
            if (data.suggested_date) {
                document.getElementById('payment_next_date').value = data.suggested_date;
            }
            if (data.absences > 0) {
                const hint = document.getElementById('absences_hint');
                hint.textContent = `⚠️ ${data.absences} faltas desde el último pago. Considere un descuento.`;
                hint.classList.remove('hidden');
            }
        })
        .catch(err => {
            console.error("Error billing info", err);
            const today = new Date();
            today.setMonth(today.getMonth() + 1);
            document.getElementById('payment_next_date').valueAsDate = today;
        });
    
    document.getElementById('paymentModal').classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

function closePaymentModal() {
    document.getElementById('paymentModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
}

function openSettingsModal(id, name, amount, date, plan) {
    document.getElementById('settings_patient_id').value = id;
    document.getElementById('settings_patient_name').textContent = name;
    document.getElementById('settings_amount').value = amount;
    document.getElementById('settings_plan').value = plan.toLowerCase();
    
    if (date && date !== 'None') {
        document.getElementById('settings_date').value = date;
    } else {
        document.getElementById('settings_date').value = '';
    }
    
    document.getElementById('settingsModal').classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

function closeSettingsModal() {
    document.getElementById('settingsModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
}

function filterPayments() {
    const searchInput = document.getElementById('searchInput').value.toLowerCase();
    const therapistFilter = document.getElementById('therapistFilter').value;
    const sedeFilter = document.getElementById('sedeFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    
    const checkRowData = (name, therapistText, sede, status, lastPayment, debt) => {
        const matchName = name.includes(searchInput);
        const matchTherapist = (therapistFilter === 'all') || (therapistText.includes(therapistFilter));
        const matchSede = (sedeFilter === 'all') || (sede === sedeFilter);
        
        let matchStatus = true;
        const debtNum = parseFloat(debt);
        if (statusFilter === 'debt') {
            matchStatus = (status === 'overdue' || (debtNum > 0.5 && status === 'active') || status === 'debt');
        } else if (statusFilter === 'paid') {
            matchStatus = (status === 'active' && debtNum <= 0.5);
        } else if (statusFilter === 'inactive') {
            matchStatus = (status === 'inactive');
        } 
        
        let matchAge = true;
        if (activeAgeFilter) {
            let diffDays = 9999;
            if (lastPayment && lastPayment !== 'None') {
                const pDate = new Date(lastPayment);
                const today = new Date();
                // Normalize both to start of day to avoid timezone offsets causing 1-day diffs
                const utc1 = Date.UTC(pDate.getFullYear(), pDate.getMonth(), pDate.getDate());
                const utc2 = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
                const diffTime = Math.abs(utc2 - utc1);
                diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
            }
            if (activeAgeFilter === '0-30') matchAge = diffDays <= 30;
            else if (activeAgeFilter === '30-60') matchAge = diffDays > 30 && diffDays <= 60;
            else if (activeAgeFilter === '60-90') matchAge = diffDays > 60 && diffDays <= 90;
            else if (activeAgeFilter === '90+') matchAge = diffDays > 90;
        }

        return matchName && matchTherapist && matchSede && matchStatus && matchAge;
    };
    
    // Desktop & Mobile Filter
    document.querySelectorAll('.payment-row, .payment-card').forEach(el => {
        const name = (el.dataset.name || '').toLowerCase();
        // Handle therapist text difference between row and card
        let therapistText = '';
        if(el.classList.contains('payment-row')) {
             therapistText = el.querySelector('.therapist-cell') ? el.querySelector('.therapist-cell').textContent.trim() : '';
        } else {
             const tDiv = el.querySelector('.therapist-name');
             therapistText = tDiv ? tDiv.textContent.trim() : '';
        }
        
        const sede = el.dataset.sede || 'none';
        const status = el.dataset.status || 'active';
        const lastPayment = el.dataset.lastPayment || 'None';
        const debt = el.dataset.debt || '0';
        
        if (checkRowData(name, therapistText, sede, status, lastPayment, debt)) {
            el.style.display = "";
        } else {
            el.style.display = "none";
        }
    });

    sortPayments();
}

function sortPayments() {
    const sortValue = document.getElementById('sortFilter').value;
    const sortFunction = (a, b) => {
        let valA, valB;
        if (sortValue === 'name') {
             valA = a.dataset.name || '';
             valB = b.dataset.name || '';
             return valA.localeCompare(valB);
        } else if (sortValue === 'date_asc') {
             valA = a.dataset.dueDate || '';
             valB = b.dataset.dueDate || '';
             return valA.localeCompare(valB);
        } else if (sortValue === 'date_desc') {
             valA = a.dataset.dueDate || '';
             valB = b.dataset.dueDate || '';
             return valB.localeCompare(valA);
        } else if (sortValue === 'debt_desc') {
             valA = parseFloat(a.dataset.debt || 0);
             valB = parseFloat(b.dataset.debt || 0);
             return valB - valA;
        }
        return 0;
    };

    const tbody = document.querySelector('tbody');
    if(tbody) {
        const rows = Array.from(document.querySelectorAll('tr.payment-row'));
        rows.sort(sortFunction);
        rows.forEach(row => tbody.appendChild(row));
    }
    const mobileContainer = document.querySelector('.md\\:hidden.space-y-4');
    if (mobileContainer) {
        const cards = Array.from(document.querySelectorAll('div.payment-card'));
        cards.sort(sortFunction);
        cards.forEach(card => mobileContainer.appendChild(card));
    }
    
    // Save state after sort
    saveState();
}

// --- LocalStorage Logic ---
function saveState() {
    const state = {
        search: document.getElementById('searchInput').value,
        therapist: document.getElementById('therapistFilter').value,
        sede: document.getElementById('sedeFilter').value,
        status: document.getElementById('statusFilter').value,
        sort: document.getElementById('sortFilter').value,
        ageFilter: activeAgeFilter,
        timestamp: new Date().getTime()
    };
    localStorage.setItem('moscowle_payments_state', JSON.stringify(state));
}

function loadState() {
    const saved = localStorage.getItem('moscowle_payments_state');
    if (!saved) return;
    
    try {
        const state = JSON.parse(saved);
        // Clean up old state if needed (optional expiration)
        const ONE_DAY = 24 * 60 * 60 * 1000;
        if (new Date().getTime() - state.timestamp > ONE_DAY) {
            localStorage.removeItem('moscowle_payments_state');
            return;
        }

        if(state.search !== undefined) document.getElementById('searchInput').value = state.search;
        if(state.therapist) document.getElementById('therapistFilter').value = state.therapist;
        if(state.sede) document.getElementById('sedeFilter').value = state.sede;
        if(state.status) document.getElementById('statusFilter').value = state.status;
        if(state.sort) document.getElementById('sortFilter').value = state.sort;
        if(state.ageFilter) {
            activeAgeFilter = state.ageFilter;
            // Restore visual badge for age filter
            const filterBadge = document.getElementById('ageFilterBadge'); // Assuming ID exists or will be found via parent
            const container = document.getElementById('filter-feedback-container');
            if (container) {
                 container.classList.remove('hidden');
                 const textSpan = document.getElementById('active-age-filter-text');
                 if(textSpan) textSpan.textContent = state.ageFilter + ' días'; // Approximate label
            }
        }
    } catch (e) {
        console.error("Error loading state", e);
    }
}

function cacheData(data) {
    try {
        localStorage.setItem('moscowle_patients_data', JSON.stringify({
            data: data,
            timestamp: new Date().getTime()
        }));
    } catch (e) {
        console.warn('Quota exceeded for localStorage', e);
    }
}
// ---------------------------

function analyzeReceipt(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('receipt', file);
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;
    if (csrfToken) formData.append('csrf_token', csrfToken);

    const spinner = document.getElementById('scan_spinner');
    spinner.classList.remove('hidden');
    
    fetch("/admin/analyze-receipt", {
        method: 'POST',
        body: formData,
        headers: {'X-CSRFToken': csrfToken}
    })
    .then(response => response.json())
    .then(data => {
        spinner.classList.add('hidden');
        if (data.error) { console.warn("Scan Error:", data.error); return; }
        
        if (data.amount) {
            const el = document.getElementById('payment_amount');
            el.value = data.amount; animateField(el);
        }
        if (data.date) {
            const el = document.getElementById('payment_date');
            el.value = data.date; animateField(el);
        }
        if (data.reference) {
            const el = document.querySelector('input[name="reference"]');
            el.value = data.reference; animateField(el);
        }
        if (data.method) {
            const el = document.querySelector('select[name="method"]');
            let val = data.method.toLowerCase();
            let final = 'transferencia';
            if (val.includes('yape') || val.includes('plin')) final = 'yape';
            else if (val.includes('effec') || val.includes('cash')) final = 'efectivo';
            else if (val.includes('tarj') || val.includes('card')) final = 'tarjeta';
            el.value = final; animateField(el);
        }
        if (data.discount && data.discount > 0) {
             const el = document.getElementById('payment_discount');
             el.value = data.discount; animateField(el);
        }
    })
    .catch(err => {
        console.error("Error scanning:", err);
        spinner.classList.add('hidden');
    });
}

function animateField(element) {
    element.classList.add('bg-green-50', 'transition-colors', 'duration-500');
    setTimeout(() => {
        element.classList.remove('bg-green-50');
    }, 1500);
}

function clearAgeFilter() {
    activeAgeFilter = null;
    document.getElementById('filter-feedback-container').classList.add('hidden');
    filterPayments();
}

function initDashboard(patientsFromJinja) {
    const patients = patientsFromJinja;

    // Cache Data & Load State
    cacheData(patients);
    loadState();

    let totalDebt = 0;
    let totalRevenueExpected = 0; 
    let countActive = 0;
    let countOverdue = 0;
    let countInactive = 0;
    
    const statusCounts = { active: 0, overdue: 0, inactive: 0 };
    const debtBySede = {};
    const lastPaymentMonths = { '0-30 días': 0, '30-60 días': 0, '60-90 días': 0, '+90 días': 0 };
    const today = new Date();

    patients.forEach(p => {
         if (p.status === 'active') countActive++;
         if (p.status === 'overdue') countOverdue++;
         if (p.status === 'inactive') countInactive++;
         
         const sKey = (p.status === 'active' || p.status === 'overdue' || p.status === 'inactive') ? p.status : 'inactive';
         statusCounts[sKey] = (statusCounts[sKey] || 0) + 1;
         totalDebt += (p.debt > 0 ? p.debt : 0);
         if (p.status === 'active') totalRevenueExpected += (p.paid || 0);

         if (p.debt > 0.5) {
             const sedeName = p.sede || 'Sin Sede';
             debtBySede[sedeName] = (debtBySede[sedeName] || 0) + p.debt;
         }
         
         if (p.lastVal !== 'None') {
             const diffTime = Math.abs(today - new Date(p.lastVal));
             const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
             if(diffDays <= 30) lastPaymentMonths['0-30 días']++;
             else if(diffDays <= 60) lastPaymentMonths['30-60 días']++;
             else if(diffDays <= 90) lastPaymentMonths['60-90 días']++;
             else lastPaymentMonths['+90 días']++;
         } else {
             lastPaymentMonths['+90 días']++;
         }
    });
    
    document.getElementById('kpi_total_debt').textContent = `S/ ${totalDebt.toFixed(2)}`;
    document.getElementById('kpi_active_users').textContent = countActive;
    document.getElementById('kpi_overdue_users').textContent = countOverdue + countInactive;
    document.getElementById('kpi_total_revenue').textContent = `S/ ${totalRevenueExpected.toFixed(2)}`;
    
    if (document.getElementById('chartStatus')) {
        new Chart(document.getElementById('chartStatus'), {
            type: 'doughnut',
            data: {
                labels: ['Activos', 'Vencidos / Deuda', 'Inactivos'],
                datasets: [{
                    data: [statusCounts.active, statusCounts.overdue, statusCounts.inactive],
                    backgroundColor: ['#10B981', '#EF4444', '#9CA3AF'],
                    borderWidth: 0
                }]
            },
            options: { 
                responsive: true, maintainAspectRatio: false, 
                plugins: { legend: { position: 'right' } },
                onClick: (evt, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const statusMap = ['paid', 'debt', 'inactive'];
                        document.getElementById('statusFilter').value = statusMap[index];
                        filterPayments();
                        document.querySelector('.bg-surface').scrollIntoView({behavior: 'smooth'});
                    }
                }
            }
        });
    }

    if (document.getElementById('chartDebtSede')) {
        new Chart(document.getElementById('chartDebtSede'), {
            type: 'bar',
            data: {
                labels: Object.keys(debtBySede),
                datasets: [{
                    label: 'Deuda Total (S/)',
                    data: Object.values(debtBySede),
                    backgroundColor: '#F59E0B',
                    borderRadius: 4
                }]
            },
            options: { 
                responsive: true, maintainAspectRatio: false, 
                plugins: { legend: { display: false } },
                onClick: (evt, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const sedeName = Object.keys(debtBySede)[index];
                        const filterEl = document.getElementById('sedeFilter');
                        for(let i=0; i<filterEl.options.length; i++){
                            if(filterEl.options[i].value === sedeName){
                                filterEl.selectedIndex = i; break;
                            }
                        }
                        filterPayments();
                        document.getElementById('statusFilter').value = 'debt';
                        filterPayments();
                        document.querySelector('.bg-surface').scrollIntoView({behavior: 'smooth'});
                    }
                } 
            }
        });
    }
    
    if (document.getElementById('chartLastPayment')) {
        new Chart(document.getElementById('chartLastPayment'), {
            type: 'bar',
            data: {
                labels: Object.keys(lastPaymentMonths),
                datasets: [{
                    label: 'Cantidad de Pacientes',
                    data: Object.values(lastPaymentMonths),
                    backgroundColor: ['#3B82F6', '#8B5CF6', '#EC4899', '#6B7280'],
                    borderRadius: 4
                }]
            },
            options: { 
                indexAxis: 'y', responsive: true, maintainAspectRatio: false, 
                plugins: { legend: { display: false } },
                onClick: (evt, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const labels = Object.keys(lastPaymentMonths);
                        const selectedLabel = labels[index]; 
                        let filterCode = null;
                        if (selectedLabel.includes('0-30')) filterCode = '0-30';
                        else if (selectedLabel.includes('30-60')) filterCode = '30-60';
                        else if (selectedLabel.includes('60-90')) filterCode = '60-90';
                        else filterCode = '90+';
                        
                        if (activeAgeFilter === filterCode) {
                            activeAgeFilter = null;
                            document.getElementById('filter-feedback-container').classList.add('hidden');
                        } else {
                            activeAgeFilter = filterCode;
                            document.getElementById('filter-feedback-container').classList.remove('hidden');
                            document.getElementById('active-age-filter-text').textContent = selectedLabel;
                        }
                        filterPayments();
                        document.querySelector('.bg-surface').scrollIntoView({behavior: 'smooth'});
                    }
                }
            }
        });
    }
    filterPayments();
    filterHistory(); // Initial filter for history too
}

function filterHistory() {
    const searchInput = document.getElementById('searchInput').value.toLowerCase();
    const monthFilter = document.getElementById('monthFilter').value;
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1; // 1-12

    document.querySelectorAll('.history-row').forEach(row => {
        const text = (row.dataset.text || '').toLowerCase();
        const rowMonth = parseInt(row.dataset.month || '0');
        const rowYear = parseInt(row.dataset.year || '0');
        
        const matchSearch = text.includes(searchInput);
        
        let matchMonth = true;
        if (monthFilter !== 'all') {
            if (monthFilter === 'current') {
                matchMonth = (rowMonth === currentMonth && rowYear === currentYear);
            } else if (monthFilter === 'last') {
                let targetMonth = currentMonth - 1;
                let targetYear = currentYear;
                if (targetMonth === 0) {
                    targetMonth = 12;
                    targetYear = currentYear - 1;
                }
                matchMonth = (rowMonth === targetMonth && rowYear === targetYear);
            } else {
                // Specific month (01-12) - restricting to current year for clarity
                // Unless user wants all history? Let's stick to current year for specific months to be safe on "12 this year" issue.
                matchMonth = (parseInt(monthFilter) === rowMonth && rowYear === currentYear);
            }
        }
        
        row.style.display = (matchSearch && matchMonth) ? '' : 'none';
    });
}
