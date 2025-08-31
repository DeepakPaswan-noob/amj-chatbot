from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import re
from datetime import datetime
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from difflib import SequenceMatcher
import os
import json
import io
import csv

# Optional Redis cache
REDIS_AVAILABLE = False
redis_client = None
try:
    import redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    REDIS_AVAILABLE = False

# Optional translator (googletrans fallback)
TRANSLATOR_AVAILABLE = False
translator = None
try:
    from googletrans import Translator
    translator = Translator()
    TRANSLATOR_AVAILABLE = True
except Exception:
    TRANSLATOR_AVAILABLE = False

# Optional AI embeddings
AI_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer, util
    AI_AVAILABLE = True
except Exception as e:
    print(f"AI packages unavailable or failed to load: {e}")
    AI_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# NLTK setup
for pkg, path in [("punkt", 'tokenizers/punkt'), ("stopwords", 'corpora/stopwords'), ("wordnet", 'corpora/wordnet')]:
    try:
        nltk.data.find(path)
    except LookupError:
        nltk.download(pkg)

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))


class StudentChatbot:
    def __init__(self):
        self.model = None
        if AI_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✓ Embedding model loaded")
            except Exception as e:
                print(f"⚠ Could not load embedding model: {e}")
                self.model = None
        self.faq_embeddings = None
        self.knowledge_base = []

        self.init_database()
        self.populate_default_faqs()
        self.apply_content_updates()
        self.load_knowledge_base()

    def db(self):
        return sqlite3.connect('chatbot.db')

    def init_database(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS faqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT,
                keywords TEXT
            )'''
        )
        cur.execute(
            '''CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faq_id INTEGER,
                helpful INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )'''
        )
        conn.commit()
        conn.close()

    def populate_default_faqs(self):
        conn = self.db()
        cur = conn.cursor()

        default_faqs = [
            {
                "question": "What is Agurchand Manmull Jain College?",
                "answer": (
                    "Agurchand Manmull Jain College (AMJC) is a premier institution in Chennai, affiliated to the University of Madras and reaccredited by NAAC. "
                    "It offers undergraduate, postgraduate and research programs across Commerce, Science and Arts. "
                    "Learn more: <a href='https://www.amjaincollege.edu.in/about-us/' target='_blank'>About Us</a>."
                ),
                "category": "general",
                "keywords": "amjc about college chennai madras university"
            },
            {
                "question": "How do I apply for admission?",
                "answer": (
                    "Apply online for 2025–26:\n"
                    "• <a href='http://115.96.66.234/amjainonline/onlineapplication/transaction/applicantRegistrationShiftI.jsp' target='_blank'>Shift I – Apply</a><br>"
                    "• <a href='http://application.amjaincollege.edu.in/amjainonline/onlineapplication/loginManager/youLogin.jsp' target='_blank'>Shift II – Apply</a><br>"
                    "Details: <a href='https://www.amjaincollege.edu.in/admissions/' target='_blank'>Admissions</a>."
                ),
                "category": "admissions",
                "keywords": "admission apply online shift i shift ii application portal"
            },
            {
                "question": "hi",
                "answer": (
                    "Hi 👋! I'm AM Jain College assistant. Ask me about Admissions, Courses, Placements, Fees, or Contact details."
                ),
                "category": "general",
                "keywords": "hi hello hey greeting"
            },
            {
                "question": "What is the fee structure?",
                "answer": (
                    "Fees vary by course and shift. For the latest fee details, please contact the admissions office or see the Admissions page.<br>"
                    "Shift I: <a href='tel:+914446622216'>044-46622216</a> • "
                    "<a href='mailto:shift1@amjaincollege.edu.in'>shift1@amjaincollege.edu.in</a><br>"
                    "Shift II: <a href='tel:+914446622211'>044-46622211</a> • "
                    "<a href='mailto:shift2@amjaincollege.edu.in'>shift2@amjaincollege.edu.in</a><br>"
                    "More info: <a href='https://www.amjaincollege.edu.in/admissions/' target='_blank'>Admissions</a>"
                ),
                "category": "admissions",
                "keywords": "fee fees tuition course fee structure admission"
            },
            {
                "question": "fees",
                "answer": (
                    "💰 <b>Fee Overview</b><br>Undergraduate (average): ₹35,000 – ₹50,000 / year<br>Postgraduate (average): ₹50,000 – ₹70,000 / year<br>Payment: Online / Offline (Cash / Cheque / DD).<br>Contact: <a href='tel:+914426630520'>044-26630520</a>."
                ),
                "category": "fees",
                "keywords": "fees fee tuition"
            },
            {
                "question": "B.Com (ISM) fees",
                "answer": (
                    "🎓 <b>B.Com (Information System Management) - Fees (approx)</b><br>Average annual fee: <b>₹35,000 – ₹50,000</b> (may vary by shift and year).<br>Payment modes: Online / Offline (Cash / Cheque / DD).<br>For exact, up-to-date fees and scholarship options, contact Admissions:<br>☎️ <a href='tel:+914446622216'>044-46622216</a> (Shift 1) | <a href='tel:+914446622211'>044-46622211</a> (Shift 2)<br>📧 <a href='mailto:shift1@amjaincollege.edu.in'>shift1@amjaincollege.edu.in</a>, <a href='mailto:shift2@amjaincollege.edu.in'>shift2@amjaincollege.edu.in</a>"
                ),
                "category": "fees",
                "keywords": "bcom ism b.com ism fees fee"
            },
            {
                "question": "B.Com (CA) fees",
                "answer": (
                    "🎓 <b>B.Com (Computer Applications) - Fees (approx)</b><br>Average annual fee: <b>₹35,000 – ₹50,000</b> (may vary by shift and year).<br>Payment modes: Online / Offline. For exact fees contact Admissions: ☎️ <a href='tel:+914446622216'>044-46622216</a>."
                ),
                "category": "fees",
                "keywords": "bcom ca b.com ca fees fee"
            },
            {
                "question": "B.Sc (Computer Science) fees",
                "answer": (
                    "🎓 <b>B.Sc (Computer Science) - Fees (approx)</b><br>Average annual fee: <b>₹35,000 – ₹55,000</b> (may vary by program/shift).<br>Contact Admissions: ☎️ <a href='tel:+914446622216'>044-46622216</a>."
                ),
                "category": "fees",
                "keywords": "bsc cs b.sc cs fees fee"
            },
            {
                "question": "B.A (English) fees",
                "answer": (
                    "🎓 <b>B.A (English) - Fees (approx)</b><br>Average annual fee: <b>₹30,000 – ₹45,000</b>.<br>Contact Admissions: ☎️ <a href='tel:+914446622216'>044-46622216</a>."
                ),
                "category": "fees",
                "keywords": "ba english b.a english fees fee"
            },
            {
                "question": "B.A (Economics) fees",
                "answer": (
                    "🎓 <b>B.A (Economics) - Fees (approx)</b><br>Average annual fee: <b>₹30,000 – ₹45,000</b>.<br>Contact Admissions: ☎️ <a href='tel:+914446622216'>044-46622216</a>."
                ),
                "category": "fees",
                "keywords": "ba economics b.a economics fees fee"
            },
            {
                "question": "M.Com fees",
                "answer": (
                    "🎓 <b>M.Com - Fees (approx)</b><br>Average annual fee: <b>₹50,000 – ₹70,000</b>.<br>Contact Admissions: ☎️ <a href='tel:+914446622216'>044-46622216</a>."
                ),
                "category": "fees",
                "keywords": "mcom m.com fees fee"
            },
            {
                "question": "M.Sc (Computer Science) fees",
                "answer": (
                    "🎓 <b>M.Sc (Computer Science) - Fees (approx)</b><br>Average annual fee: <b>₹50,000 – ₹75,000</b>.<br>Contact Admissions: ☎️ <a href='tel:+914446622216'>044-46622216</a>."
                ),
                "category": "fees",
                "keywords": "msc cs m.sc cs fees fee"
            },
            {
                "question": "What courses are offered?",
                "answer": (
                    "Explore programs by school:<br>"
                    "• <a href='https://www.amjaincollege.edu.in/school-of-commerce/' target='_blank'>School of Commerce</a><br>"
                    "• <a href='https://www.amjaincollege.edu.in/school-of-science/' target='_blank'>School of Science</a><br>"
                    "• <a href='https://www.amjaincollege.edu.in/school-of-arts/' target='_blank'>School of Arts</a>"
                ),
                "category": "courses",
                "keywords": "courses programs commerce science arts departments"
            },
            {
                "question": "What are the college facilities?",
                "answer": (
                    "AMJC offers library, laboratories, sports, clubs and more. See campus life: "
                    "<a href='https://www.amjaincollege.edu.in/life-amj/' target='_blank'>Life@AMJC</a>."
                ),
                "category": "facilities",
                "keywords": "facilities library labs sports clubs campus life"
            },
            {
                "question": "How can I contact the college?",
                "answer": (
                    "Contact:<br>"
                    "Shift I: <a href='tel:+914446622216'>044-46622216</a> | <a href='mailto:shift1@amjaincollege.edu.in'>shift1@amjaincollege.edu.in</a><br>"
                    "Shift II: <a href='tel:+914446622211'>044-46622211</a> | <a href='mailto:shift2@amjaincollege.edu.in'>shift2@amjaincollege.edu.in</a><br>"
                    "More: <a href='https://www.amjaincollege.edu.in/contact-us/' target='_blank'>Contact Us</a>"
                ),
                "category": "contact",
                "keywords": "contact phone email address shift1 shift2"
            },
            {
                "question": "Do you have a gallery or LMS?",
                "answer": (
                    "Yes:<br>"
                    "• <a href='https://www.amjaincollege.edu.in/gallery/' target='_blank'>Gallery</a><br>"
                    "• <a href='https://www.amjaincollege.edu.in/lms/' target='_blank'>LMS Portal</a>"
                ),
                "category": "facilities",
                "keywords": "gallery photos lms portal e-learning"
            },
            {
                "question": "What about placements?",
                "answer": (
                    "Top recruiters include ICICI Bank, Infosys, TATA, Wipro, HCL and more. "
                    "Details: <a href='https://www.amjaincollege.edu.in/placements-training/' target='_blank'>Placements</a>."
                ),
                "category": "placements",
                "keywords": "placement recruiters jobs career training"
            },
            {
                "question": "Where is AMJC located?",
                "answer": (
                    "Meenambakkam, Chennai – 600061, Tamil Nadu, India. "
                    "<a href='https://www.amjaincollege.edu.in/contact-us/' target='_blank'>Contact Us</a>."
                ),
                "category": "general",
                "keywords": "location address meenambakkam chennai"
            },
            {
                "question": "Social media links",
                "answer": (
                    "Follow AMJC:<br>"
                    "• <a href='https://www.instagram.com/amjaincollege_official/' target='_blank'>Instagram</a><br>"
                    "• <a href='https://in.linkedin.com/school/amjc/' target='_blank'>LinkedIn</a><br>"
                    "• <a href='https://www.facebook.com/amjaincollegechennai' target='_blank'>Facebook</a>"
                ),
                "category": "contact",
                "keywords": "social instagram linkedin facebook"
            },
            {
                "question": "What are the entrance exam requirements?",
                "answer": (
                    "Entrance exam requirements depend on the specific program:"
                    "<ul>"
                    "<li>Some courses may require entrance exams</li>"
                    "<li>Others may have merit-based admission</li>"
                    "<li>Certain programs follow University of Madras guidelines</li>"
                    "</ul>"
                    "For accurate information about your chosen course:<br>"
                    "Shift I: <a href='tel:+914446622216'>044-46622216</a> • "
                    "<a href='mailto:shift1@amjaincollege.edu.in'>shift1@amjaincollege.edu.in</a><br>"
                    "Shift II: <a href='tel:+914446622211'>044-46622211</a> • "
                    "<a href='mailto:shift2@amjaincollege.edu.in'>shift2@amjaincollege.edu.in</a><br>"
                    "See also: <a href='https://www.amjaincollege.edu.in/admissions/' target='_blank'>Admissions page</a>."
                ),
                "category": "admissions",
                "keywords": "entrance exam requirement merit-based university of madras guidelines admission"
            },
        ]

        # Insert each FAQ if not already present (idempotent seeding)
        for faq in default_faqs:
            cur.execute('SELECT COUNT(*) FROM faqs WHERE question = ?', (faq['question'],))
            exists = cur.fetchone()[0]
            if not exists:
                cur.execute(
                    'INSERT INTO faqs (question, answer, category, keywords) VALUES (?, ?, ?, ?)',
                    (faq['question'], faq['answer'], faq.get('category', ''), faq.get('keywords', ''))
                )
        conn.commit()
        conn.close()

    # Admin CRUD helpers
    def add_faq(self, question, answer, category='', keywords=''):
        conn = self.db()
        cur = conn.cursor()
        cur.execute('INSERT INTO faqs (question, answer, category, keywords) VALUES (?, ?, ?, ?)',
                    (question, answer, category, keywords))
        conn.commit()
        conn.close()

    def update_faq(self, faq_id, question, answer, category='', keywords=''):
        conn = self.db()
        cur = conn.cursor()
        cur.execute('UPDATE faqs SET question=?, answer=?, category=?, keywords=? WHERE id=?',
                    (question, answer, category, keywords, faq_id))
        conn.commit()
        conn.close()

    def delete_faq(self, faq_id):
        conn = self.db()
        cur = conn.cursor()
        cur.execute('DELETE FROM faqs WHERE id=?', (faq_id,))
        conn.commit()
        conn.close()

    def apply_content_updates(self):
        """Apply idempotent content fixes/updates to existing FAQs in the DB."""
        conn = self.db()
        cur = conn.cursor()
        new_answer = (
            "Entrance exam requirements depend on the specific program:"
            "<ul>"
            "<li>Some courses may require entrance exams</li>"
            "<li>Others may have merit-based admission</li>"
            "<li>Certain programs follow University of Madras guidelines</li>"
            "</ul>"
            "For accurate information about your chosen course:<br>"
            "Shift I: <a href='tel:+914446622216'>044-46622216</a> • "
            "<a href='mailto:shift1@amjaincollege.edu.in'>shift1@amjaincollege.edu.in</a><br>"
            "Shift II: <a href='tel:+914446622211'>044-46622211</a> • "
            "<a href='mailto:shift2@amjaincollege.edu.in'>shift2@amjaincollege.edu.in</a><br>"
            "See also: <a href='https://www.amjaincollege.edu.in/admissions/' target='_blank'>Admissions page</a>."
        )
        new_keywords = "entrance exam requirement merit-based university of madras guidelines admission"
        cur.execute(
            "UPDATE faqs SET answer = ?, category = 'admissions', keywords = ? WHERE lower(question) LIKE '%entrance%'",
            (new_answer, new_keywords)
        )
        conn.commit()
        conn.close()

    def load_knowledge_base(self):
        conn = self.db()
        cur = conn.cursor()
        cur.execute('SELECT id, question, answer, category, keywords FROM faqs')
        self.knowledge_base = cur.fetchall()
        conn.close()

        if AI_AVAILABLE and self.model and self.knowledge_base:
            try:
                texts = [q + ' ' + (k or '') for _id, q, a, c, k in self.knowledge_base]
                self.faq_embeddings = self.model.encode(texts, convert_to_tensor=True)
                print(f"✓ Created embeddings for {len(texts)} FAQs")
            except Exception as e:
                print(f"⚠ Embeddings disabled due to error: {e}")
                self.faq_embeddings = None

    def preprocess(self, text: str):
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        tokens = [lemmatizer.lemmatize(t) for t in word_tokenize(text) if t not in stop_words]
        return tokens

    def apply_synonyms(self, text: str):
        # simple synonyms mapping to broaden matching
        synonyms = {
            'fee': 'fees',
            'tuition': 'fees',
            'placement': 'placements',
            'salary': 'placements',
            'admission': 'admissions',
            'apply': 'admissions'
        }
        words = text.split()
        words = [synonyms.get(w, w) for w in words]
        return ' '.join(words)

    def keyword_match_score(self, q_tokens, u_tokens, q_text, u_text):
        overlap = len(set(q_tokens) & set(u_tokens))
        substr = 1 if any(t in q_text for t in u_tokens if len(t) > 3) else 0
        fuzzy = SequenceMatcher(None, q_text, u_text).ratio()
        score = overlap * 0.4 + substr * 0.2 + fuzzy * 0.6
        return min(score, 1.0)

    def find_best_match(self, user_message: str):
        user_text = user_message.strip()
        if not user_text:
            return None, 0.0

        # apply simple synonyms normalization
        user_text = self.apply_synonyms(user_text)

        # Try embeddings first
        if AI_AVAILABLE and self.model and self.faq_embeddings is not None:
            try:
                emb = self.model.encode([user_text], convert_to_tensor=True)
                sims = util.cos_sim(emb, self.faq_embeddings)[0]
                best_idx = int(sims.argmax())
                best_score = float(sims[best_idx])
                return self.knowledge_base[best_idx], best_score
            except Exception as e:
                print(f"⚠ Embedding match failed: {e}")

        # Fallback: keyword/fuzzy
        u_tokens = self.preprocess(user_text)
        u_text = ' '.join(u_tokens)
        best = None
        best_score = 0.0
        for i, row in enumerate(self.knowledge_base):
            # row: (id, question, answer, category, keywords)
            fid, q, a, c, k = row
            q_tokens = self.preprocess(q + ' ' + (k or ''))
            q_text = ' '.join(q_tokens)
            # consider synonyms in FAQ text as well
            q_text = self.apply_synonyms(q_text)
            score = self.keyword_match_score(q_tokens, u_tokens, q_text, u_text)
            if score > best_score:
                best_score = score
                best = row
        return best, best_score

    def get_response(self, user_message: str):
        match, score = self.find_best_match(user_message)
        threshold = 0.48 if (self.faq_embeddings is None) else 0.40
        if not match or score < threshold:
            fallback = (
                "I couldn't find an exact match. Please check 👉 <a href='https://www.amjaincollege.edu.in/' target='_blank'>AM Jain College Website</a> or contact 044-26630520."
            )
            return fallback, None
        # match is row: (id, question, answer, category, keywords)
        return match[2], match[0]


bot = StudentChatbot()


@app.route('/')
def index():
    # expose whether translator is available so the UI can disable language options
    return render_template('index.html', translator_available=TRANSLATOR_AVAILABLE)


@app.route('/admin')
def admin_panel():
    # simple admin page (could be extended with auth)
    conn = bot.db()
    cur = conn.cursor()
    cur.execute('SELECT id, question, category FROM faqs ORDER BY id DESC')
    faqs = cur.fetchall()
    conn.close()
    return render_template('admin.html', faqs=faqs)


@app.route('/api/faqs', methods=['GET', 'POST'])
def api_faqs():
    if request.method == 'GET':
        conn = bot.db()
        cur = conn.cursor()
        cur.execute('SELECT id, question, answer, category, keywords FROM faqs')
        rows = cur.fetchall()
        conn.close()
        return jsonify([{'id': r[0], 'question': r[1], 'answer': r[2], 'category': r[3], 'keywords': r[4]} for r in rows])

    data = request.get_json(force=True)
    q = data.get('question')
    a = data.get('answer')
    cat = data.get('category', '')
    kw = data.get('keywords', '')
    bot.add_faq(q, a, cat, kw)
    bot.load_knowledge_base()
    return jsonify({'status': 'ok'})


@app.route('/api/faqs/<int:faq_id>', methods=['PUT', 'DELETE'])
def api_faq_modify(faq_id):
    if request.method == 'DELETE':
        bot.delete_faq(faq_id)
        bot.load_knowledge_base()
        return jsonify({'status': 'deleted'})

    data = request.get_json(force=True)
    bot.update_faq(faq_id, data.get('question'), data.get('answer'), data.get('category', ''), data.get('keywords', ''))
    bot.load_knowledge_base()
    return jsonify({'status': 'updated'})


@app.route('/api/vote', methods=['POST'])
def api_vote():
    data = request.get_json(force=True)
    faq_id = data.get('faq_id')
    helpful = 1 if data.get('helpful') else 0
    conn = bot.db()
    cur = conn.cursor()
    cur.execute('INSERT INTO votes (faq_id, helpful) VALUES (?, ?)', (faq_id, helpful))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/export/csv')
def export_csv():
    conn = bot.db()
    cur = conn.cursor()
    cur.execute('SELECT student_message, bot_response, timestamp FROM conversations ORDER BY id DESC')
    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['student_message', 'bot_response', 'timestamp'])
    for r in rows:
        writer.writerow(r)
    output.seek(0)

    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='chat_history.csv')


# PDF export removed - only CSV export is supported


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    user_msg = (data.get('message') or '').strip()
    lang = data.get('lang', 'en')
    if not user_msg:
        return jsonify({"response": "Please type a message."})

    # check cache
    cache_key = f"chat:{user_msg}" if REDIS_AVAILABLE else None
    if REDIS_AVAILABLE and redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            resp = json.loads(cached)
            return jsonify({'response': resp.get('response')})

    bot_resp, faq_id = bot.get_response(user_msg)

    # Translate if requested (best-effort)
    if TRANSLATOR_AVAILABLE and lang and lang != 'en' and bot_resp:
        try:
            trans = translator.translate(bot_resp, dest=lang)
            bot_resp = trans.text
        except Exception:
            pass

    # store conversation
    conn = bot.db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO conversations (student_message, bot_response, timestamp) VALUES (?, ?, ?)',
        (user_msg, bot_resp, datetime.now().isoformat(timespec='seconds'))
    )
    conn.commit()
    conn.close()

    # cache
    if REDIS_AVAILABLE and redis_client:
        redis_client.set(cache_key, json.dumps({'response': bot_resp}), ex=300)

    return jsonify({"response": bot_resp})





@app.route('/health')
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
