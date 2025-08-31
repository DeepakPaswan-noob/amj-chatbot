# pip install requests beautifulsoup4 trafilatura tldextract pypdf urllib3==2.2.2
import json, os, re, time, hashlib
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag
import tldextract, trafilatura, requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pypdf import PdfReader

DOMAIN = "www.amjaincollege.edu.in"  # stay on main site only
START_URLS = [
    "https://www.amjaincollege.edu.in/",
    "https://www.amjaincollege.edu.in/admissions/",
    "https://www.amjaincollege.edu.in/fee-details/",
    "https://www.amjaincollege.edu.in/contact-us/",
    "https://www.amjaincollege.edu.in/school-of-science/",
    "https://www.amjaincollege.edu.in/school-of-commerce/",
    "https://www.amjaincollege.edu.in/academic-leadership/",
    "https://www.amjaincollege.edu.in/library/",
    "https://www.amjaincollege.edu.in/academic-calendar/",
    "https://www.amjaincollege.edu.in/research-committee/",
]

# Skip obvious non-knowledge or private areas
SKIP_PATTERNS = re.compile(
    r"(?:\?(replytocom|s|share)=|/wp-admin/|/wp-json/|/tag/|/author/|/cart/|/my-account/|/login/|/iqac-private/|/feed/)",
    re.I,
)

# Basic queue-limited crawl
MAX_PAGES = 1200
TIMEOUT = 20
SLEEP_BETWEEN = 0.5  # be polite

DATA_DIR = "amjc_data"
PDF_DIR = os.path.join(DATA_DIR, "pdfs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

OUT_HTML_JSONL = os.path.join(DATA_DIR, "amjc_pages.jsonl")
OUT_PDF_JSONL  = os.path.join(DATA_DIR, "amjc_pdfs.jsonl")
OUT_CHUNKS     = os.path.join(DATA_DIR, "amjc_chunks.jsonl")

# Requests session with retries & UA
def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; AMJCChatbotCrawler/1.0; +https://www.amjaincollege.edu.in/)"
    })
    retry = Retry(total=5, backoff_factor=0.6,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET", "HEAD"])
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

session = make_session()

def same_domain(u: str) -> bool:
    try:
        p = urlparse(u)
        if p.scheme not in ("http", "https"): return False
        ext = tldextract.extract(p.netloc)
        host = f"{ext.subdomain}.{ext.domain}.{ext.suffix}".strip(".")
        return host == DOMAIN
    except Exception:
        return False

def canonicalize(u: str) -> str:
    u, _frag = urldefrag(u)
    # normalize trailing slashes a bit
    return u.rstrip("/") + ("/" if urlparse(u).path in ("", "/") else "")

def clean_text_from_html(html: str, url: str) -> str:
    # Try trafilatura first (best quality main-content extraction)
    txt = trafilatura.extract(html, url=url, include_links=False, include_tables=False, favor_recall=True)
    if txt and txt.strip():
        return txt.strip()
    # Fallback: full visible text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n").strip())

def get_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.text.strip():
        return soup.title.text.strip()
    og = soup.find("meta", property="og:title")
    return (og["content"].strip() if og and og.get("content") else "")

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def chunk(text, url, title, size=1000, overlap=150):
    text = re.sub(r"[ \t]+", " ", text).strip()
    chunks = []
    i = 0
    while i < len(text):
        part = text[i:i+size]
        if not part: break
        chunks.append({
            "id": f"{sha1(url)}_{i}",
            "url": url,
            "title": title,
            "content": part
        })
        i += max(size - overlap, 1)
    return chunks

def save_jsonl(path, rows):
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def is_pdf(resp: requests.Response) -> bool:
    ct = (resp.headers.get("Content-Type") or "").lower()
    return "application/pdf" in ct or resp.url.lower().endswith(".pdf")

def should_skip(url: str) -> bool:
    return bool(SKIP_PATTERNS.search(url))

visited = set()
q = deque(map(canonicalize, START_URLS))
pages_written = 0
pdfs_written = 0
chunk_count = 0

while q and pages_written + pdfs_written < MAX_PAGES:
    url = q.popleft()
    if url in visited or not same_domain(url) or should_skip(url):
        continue
    visited.add(url)

    try:
        r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    except Exception:
        continue

    if r.status_code != 200:
        continue

    if is_pdf(r):
        # store PDF to disk, extract text, write jsonl
        pdf_name = sha1(url) + ".pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        with open(pdf_path, "wb") as f:
            f.write(r.content)
        try:
            reader = PdfReader(pdf_path)
            txt = "\n".join(page.extract_text() or "" for page in reader.pages)
            if txt.strip():
                row = {"url": url, "title": os.path.basename(url) or "PDF", "content": txt.strip()}
                save_jsonl(OUT_PDF_JSONL, [row])
                save_jsonl(OUT_CHUNKS, chunk(txt, url, row["title"]))
                pdfs_written += 1
        except Exception:
            pass
        time.sleep(SLEEP_BETWEEN)
        continue

    # HTML page
    html = r.text
    title = get_title(html)
    text = clean_text_from_html(html, url)
    if text.strip():
        row = {"url": url, "title": title, "content": text}
        save_jsonl(OUT_HTML_JSONL, [row])
        save_jsonl(OUT_CHUNKS, chunk(text, url, title))
        pages_written += 1

    # enqueue more links
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        nxt = canonicalize(urljoin(url, a["href"]))
        if same_domain(nxt) and not should_skip(nxt) and nxt not in visited:
            q.append(nxt)

    time.sleep(SLEEP_BETWEEN)

print(f"Done. HTML pages: {pages_written}, PDFs: {pdfs_written}.")
print(f"Outputs:\n- {OUT_HTML_JSONL}\n- {OUT_PDF_JSONL}\n- {OUT_CHUNKS} (chunked for embeddings)")
