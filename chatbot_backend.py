import yaml
import re
from flask import Flask, request, jsonify
from difflib import SequenceMatcher
import re


def markdown_like_to_html(text: str) -> str:
    """Convert simple markdown-like text into HTML.

    - **bold** -> <b>bold</b>
    - lines starting with •, -, * -> <ul><li>...</li></ul>
    - lines ending with ':' -> <h4>... (no colon)</h4>
    - single newlines -> <br>
    If the text already contains HTML tags (a, ul, <), return as-is.
    """
    if not text:
        return ''

    # If already contains HTML tags, assume it's formatted
    if '<' in text and '>' in text:
        return text

    lines = text.splitlines()
    out = []
    in_list = False

    for raw in lines:
        line = raw.strip()
        if line == '':
            out.append('<br>')
            continue

        # bold replacement
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)

        # heading (ends with ':' and short)
        if line.endswith(':') and len(line) < 80:
            if in_list:
                out.append('</ul>')
                in_list = False
            title = line[:-1].strip()
            out.append(f'<h4>{title}</h4>')
            continue

        # bullet item
        if line.startswith('•') or line.startswith('-') or line.startswith('*'):
            item = line.lstrip('•-* ').strip()
            if not in_list:
                out.append('<ul>')
                in_list = True
            out.append(f'<li>{item}</li>')
            continue

        # normal paragraph line (keep emoji at start)
        if in_list:
            out.append('</ul>')
            in_list = False

        # preserve emoji positioning and add <br>
        out.append(f'{line}<br>')

    if in_list:
        out.append('</ul>')

    return ''.join(out)

app = Flask(__name__)

# Load FAQ data from YAML
with open('college_faq.yml', 'r', encoding='utf-8') as f:
    faq_data = yaml.safe_load(f)

# Preprocess questions for matching
faq_list = faq_data if isinstance(faq_data, list) else faq_data.get('faqs', [])
questions = [item['question'] for item in faq_list]

# Fuzzy match function
def find_best_match(user_query):
    user_query = user_query.lower().strip()
    best_score = 0.0
    best_idx = None
    for idx, q in enumerate(questions):
        score = SequenceMatcher(None, user_query, q.lower()).ratio()
        if score > best_score:
            best_score = score
            best_idx = idx
    if best_score > 0.55 and best_idx is not None:
        # Convert to HTML before returning so frontend can render rich text
        raw = faq_list[best_idx].get('answer', '')
        return markdown_like_to_html(raw)

    return "Sorry, I couldn't find an exact answer. Please try rephrasing or ask about admissions, fees, courses, or contact."

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    user_msg = (data.get('message') or '').strip()
    answer = find_best_match(user_msg)
    return jsonify({'response': answer})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
