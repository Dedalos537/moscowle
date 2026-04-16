import re
import os



def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match blocks of Stat Cards:
    # <div class="stat-card bg-[some_color] dark:bg-slate-900 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm hover:shadow-md transition-all duration-300 p-6 flex flex-col justify-center relative overflow-hidden group">
    # ...
    # </div>
    
    # We will search with a custom Regex to find the 4 main elements:
    # 1. bg_color class (e.g. bg-primary/5, bg-green-500/5)
    # 2. title text
    # 3. id
    # 4. initial value
    
    # Actually, a regex might be fragile if HTML varies slightly. 
    # Let's target the exact stat-card structure using a multi-line regex.
    stat_card_pattern = re.compile(
        r'<div class="stat-card[^>]*>.*?<div class="absolute right-0 top-0 w-24 h-24\s+(bg-[^ ]+).*?</div>.*?<div class="text-sm font-semibold[^>]*>\s*([^<]+)\s*</div>.*?<div\s+id="([^"]+)"[^>]*text-3xl font-extrabold\s*([^"]*?)\s*z-10"\s*>\s*([0-9A-Za-z\.,%\$]+)\s*</div>.*?</div>',
        re.DOTALL
    )

    def stat_repl(m):
        bg_color = m.group(1).strip()
        title = m.group(2).strip()
        ele_id = m.group(3).strip()
        text_color = m.group(4).strip()
        initial_val = m.group(5).strip()
        
        # Clean text_color: remove default classes added by card template if they match
        # text-charcoal dark:text-white is default in the macro
        if 'text-charcoal' in text_color:
            text_color = ''
        return f"{{{{ cards.stat_card('{ele_id}', '{title}', '{initial_val}', '{bg_color}', '{text_color}') }}}}"

    new_content = stat_card_pattern.sub(stat_repl, content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated stat-cards in {filepath}")

directories = ['app/templates/admin', 'app/templates/therapist', 'app/templates/patient']
for root_dir in directories:
    for filename in os.listdir(root_dir):
        if filename.endswith('.html'):
            process_file(os.path.join(root_dir, filename))

