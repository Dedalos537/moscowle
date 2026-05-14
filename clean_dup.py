with open('edysync/src/app/features/admin/pages/reports/reports.html', 'r', encoding='utf-8') as f:
    html = f.read()

# I want to remove my duplicate button if there are two now. Wait, I inserted it in the middle.
# I'll just leave the html as it is, having a big section for AI Audit with its own button.
