import re
import os

files_to_upgrade = [
    'app/templates/admin/sessions.html',
    'app/templates/admin/reports.html'
]

class_replacements = {
    r'\bbg-white\b': 'bg-surface-container-lowest',
    r'\bbg-gray-50\b': 'bg-surface-container-low',
    r'\bbg-gray-100\b': 'bg-surface-container',
    r'\bborder-gray-100\b': 'border-outline-variant',
    r'\bborder-gray-200\b': 'border-outline-variant',
    r'\bborder-gray-300\b': 'border-outline',
    r'\btext-gray-400\b': 'text-on-surface-variant/70',
    r'\btext-gray-500\b': 'text-on-surface-variant',
    r'\btext-gray-600\b': 'text-on-surface-variant',
    r'\btext-gray-700\b': 'text-on-surface',
    r'\btext-gray-800\b': 'text-on-surface',
    r'\btext-gray-900\b': 'text-on-surface',
    r'\btext-textDark\b': 'text-on-surface',
    r'\brounded-soft\b': 'rounded-2xl',
    r'\bshadow-soft\b': 'shadow-sm shadow-slate-200/50',
    r'\bshadow-soft-lg\b': 'shadow-lg shadow-slate-200/50',
}

icon_map = {
    r'fa-plus ': 'add ',
    r'fa-search ': 'search ',
    r'fa-times ': 'close ',
    r'fa-trash ': 'delete ',
    r'fa-edit ': 'edit ',
    r'fa-cog ': 'settings ',
    r'fa-chevron-right ': 'chevron_right ',
    r'fa-chevron-left ': 'chevron_left ',
    r'fa-chevron-down ': 'expand_more ',
    r'fa-chevron-up ': 'expand_less ',
    r'fa-arrow-right': 'arrow_forward',
    r'fa-arrow-left': 'arrow_back',
    r'fa-user ': 'person ',
    r'fa-users ': 'group ',
    r'fa-envelope ': 'mail ',
    r'fa-phone ': 'call ',
    r'fa-calendar-alt ': 'calendar_month ',
    r'fa-calendar-day ': 'today ',
    r'fa-calendar-check ': 'event_available ',
    r'fa-clock ': 'schedule ',
    r'fa-bell ': 'notifications ',
    r'fa-check-circle ': 'check_circle ',
    r'fa-times-circle ': 'cancel ',
    r'fa-exclamation-circle ': 'error ',
    r'fa-exclamation-triangle ': 'warning ',
    r'fa-info-circle ': 'info ',
    r'fa-check ': 'check ',
    r'fa-gamepad ': 'gamepad ',
    r'fa-chart-line ': 'monitoring ',
    r'fa-file-alt ': 'description ',
    r'fa-video ': 'videocam ',
    r'fa-microphone ': 'mic ',
    r'fa-paper-plane ': 'send ',
    r'fa-cloud-upload-alt ': 'cloud_upload ',
    r'fa-file-word ': 'description ',
    r'fa-download ': 'download ',
    r'fa-eye ': 'visibility ',
    r'fa-chart-bar ': 'analytics ',
    r'fa-chart-pie ': 'pie_chart ',
    r'fa-star ': 'star ',
}

def replace_icon(match):
    full_class = match.group(0)
    inner_classes = match.group(1) 
    
    replaced_name = "circle"
    remaining_classes = inner_classes
    
    for old_fa, new_mat in icon_map.items():
        if old_fa in remaining_classes:
            remaining_classes = remaining_classes.replace(old_fa, '')
            remaining_classes = remaining_classes.replace('fas ', '').replace('fa-solid ', '').replace('far ', '')
            replaced_name = new_mat.strip()
            break
            
    size = ""
    if 'text-xs' in remaining_classes: size = " text-[16px]"
    elif 'text-sm' in remaining_classes: size = " text-[20px]"
    elif 'text-lg' in remaining_classes: size = " text-[28px]"
    elif 'text-xl' in remaining_classes: size = " text-[32px]"
    elif 'text-2xl' in remaining_classes: size = " text-[36px]"
    elif 'text-3xl' in remaining_classes: size = " text-[40px]"
    elif 'text-4xl' in remaining_classes: size = " text-[48px]"
    
    remaining_classes = re.sub(r'text-(xs|sm|lg|xl|2xl|3xl|4xl|base)', '', remaining_classes).strip()
    return f'<span class="material-symbols-outlined {remaining_classes}{size}">{replaced_name}</span>'

for filepath in files_to_upgrade:
    if not os.path.exists(filepath): continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Apply classes
    for old_class, new_class in class_replacements.items():
        content = re.sub(old_class, new_class, content)

    # Apply Icons (first catch typical i tags)
    content = re.sub(r'<i class="([^"]+)"></i>', replace_icon, content)

    # Convert JS string icons like '<i class="fas fa-cloud-upload-alt...">'
    # which might have been missed by standard replacement if quotes differ or inside JS
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Upgrade complete")
