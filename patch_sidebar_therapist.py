import re

with open('edysync/src/app/core/layout/therapist-layout/therapist-layout.html', 'r', encoding='utf-8') as f:
    html = f.read()

dashboard_link = """
      <a routerLink="/therapist/dashboard" routerLinkActive="active"
         class="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-charcoal
                hover:bg-primary/5 hover:text-primary transition-all duration-200 relative
                group"
         [routerLinkActiveOptions]="{exact: true}">
        <div class="w-1.5 h-1.5 rounded-full bg-transparent group-[.active]:bg-primary absolute left-1"></div>
        <span class="material-symbols-outlined text-[20px] text-gray-400 group-[.active]:text-primary transition-colors" style="font-family: 'Material Symbols Outlined'">dashboard</span>
        Dashboard
      </a>
"""

# Insert before sessions
html = html.replace('<a routerLink="/therapist/sessions"', dashboard_link + '\n      <a routerLink="/therapist/sessions"')

with open('edysync/src/app/core/layout/therapist-layout/therapist-layout.html', 'w', encoding='utf-8') as f:
    f.write(html)
