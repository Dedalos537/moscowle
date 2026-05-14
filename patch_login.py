import re

with open('edysync/src/app/features/auth/pages/login/login.ts', 'r', encoding='utf-8') as f:
    ts_content = f.read()

new_logic = """        setTimeout(() => {
           if (user && user.role === 'admin') {
               this.router.navigate(['/admin/dashboard']); 
           } else if (user && user.role === 'terapista') {
               this.router.navigate(['/therapist/sessions']);
               // O usar window.location.href = '/therapist/dashboard' si está en Flask aún, 
               // pero viendo el código de EDYSYNC parece rutar a `/therapist/sessions`. 
               // ¡Revisaremos y usaremos el routing nativo!
           } else {
               this.router.navigate(['/']); // fallback
           }
           this.isLoading = false;
        }, 1000);"""

# Replace the block inside setTimeout
ts_content = re.sub(r'setTimeout\(\(\) => \{.+?this\.isLoading = false;\s*\}, 1000\);', new_logic, ts_content, flags=re.DOTALL)

with open('edysync/src/app/features/auth/pages/login/login.ts', 'w', encoding='utf-8') as f:
    f.write(ts_content)
