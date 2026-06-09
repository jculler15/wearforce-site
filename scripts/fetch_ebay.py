#!/usr/bin/env python3
"""
Fetch The Wearforce's active eBay listings and write them into
site/data/products.json in the exact shape the storefront expects.

Run it:   python3 scripts/fetch_ebay.py

Needs scripts/config.json with your eBay keys (copy config.example.json).
See scripts/README.md.

How it works: eBay's Browse API needs a category to search within, so we
sweep the seller's items across the category groups The Wearforce sells in
(Clothing/Shoes 11450, Sports Cards 64482 by default; configurable). Size,
brand and colour come from the listing title (which is prefixed "Size X -").
Titles are scrubbed of "deadstock"/"rare" and trailing style-code junk.
"""

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONFIG_PATH = os.path.join(HERE, "config.json")
OUTPUT_PATH = os.path.join(ROOT, "site", "data", "products.json")

OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
BROWSE_URL = "https://api.ebay.com/buy/browse/v1"
SCOPE = "https://api.ebay.com/oauth/api_scope"
DEFAULT_CATEGORIES = ["11450", "64482"]  # Clothing/Shoes/Accessories, Sports Cards


# ---------------------------------------------------------------- config
def load_config():
    # In the cloud (GitHub Actions) keys come from secure environment
    # variables; locally they come from scripts/config.json.
    env_id = os.environ.get("EBAY_CLIENT_ID")
    env_secret = os.environ.get("EBAY_CLIENT_SECRET")
    if env_id and env_secret:
        cats = os.environ.get("EBAY_CATEGORY_IDS", ",".join(DEFAULT_CATEGORIES))
        return {
            "clientId": env_id,
            "clientSecret": env_secret,
            "sellerUsername": os.environ.get("EBAY_SELLER", "thewearforce"),
            "marketplace": os.environ.get("EBAY_MARKETPLACE", "EBAY_US"),
            "categoryIds": [c.strip() for c in cats.split(",") if c.strip()],
        }

    if not os.path.exists(CONFIG_PATH):
        sys.exit("Missing scripts/config.json. Copy config.example.json and add your keys.")
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    for key in ("clientId", "clientSecret", "sellerUsername"):
        if not cfg.get(key) or "PASTE" in str(cfg.get(key)):
            sys.exit(f"config.json: please fill in '{key}'.")
    cfg.setdefault("marketplace", "EBAY_US")
    cfg.setdefault("categoryIds", DEFAULT_CATEGORIES)
    return cfg


# ---------------------------------------------------------------- eBay calls
def get_token(client_id, client_secret):
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "scope": SCOPE}).encode()
    req = urllib.request.Request(OAUTH_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", f"Basic {basic}")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["access_token"]


def browse_get(path, token, marketplace, params=None):
    url = f"{BROWSE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-EBAY-C-MARKETPLACE-ID", marketplace)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def search_seller_items(token, seller, marketplace, category_ids):
    """Sweep each category for this seller, paginate, dedupe by itemId."""
    by_id = {}
    for cat in category_ids:
        offset, limit = 0, 200
        while True:
            params = {
                "category_ids": str(cat),
                "filter": f"sellers:{{{seller}}}",
                "limit": limit,
                "offset": offset,
            }
            data = browse_get("/item_summary/search", token, marketplace, params)
            batch = data.get("itemSummaries", []) or []
            for it in batch:
                by_id[it.get("itemId")] = it
            total = data.get("total", 0)
            offset += limit
            if offset >= total or not batch:
                break
            time.sleep(0.2)
        print(f"  category {cat}: {data.get('total', 0)} listings")
    return list(by_id.values())


# ---------------------------------------------------------------- parsing
# Josh's titles are "Size <x> - <product>". The separator is " - " (spaces on
# both sides); we must NOT split on dashes inside sizes ("6-8.5") or style
# codes ("CW5883-400"). Tried in order:
SIZE_SPACED_RE = re.compile(r"^\s*size\s+(.+?)\s+-\s+(.+)$", re.I)      # Size X - Product
SIZE_PARENDASH_RE = re.compile(r"^\s*size\s+(.+?\))-\s*(.+)$", re.I)    # Size X (..)- Product
SIZE_NODASH_RE = re.compile(r"^\s*size\s+([\d.]+[ymw]?(?:\s*\([^)]*\))?)\s+(.+)$", re.I)
# reseller condition abbreviations that sometimes ride along in the title/size.
# Note: do NOT include bare "new" here — it would eat "New Balance"/"New Era".
SIZE_NOISE_RE = re.compile(r"\b(clean|ds|nib|vnds|nds|euc)\b!*", re.I)
LEAD_JUNK_RE = re.compile(r"^\s*(clean|ds|nib|vnds|nds|euc)\b!*\s*-?\s*", re.I)

BRAND_CANON = [
    # sneakers
    ("air jordan", "Jordan"), ("jordan", "Jordan"), ("nike", "Nike"),
    ("yeezy", "Yeezy"), ("new balance", "New Balance"), ("adidas", "Adidas"),
    ("converse", "Converse"), ("vans", "Vans"), ("puma", "Puma"),
    ("reebok", "Reebok"), ("asics", "ASICS"), ("under armour", "Under Armour"),
    ("crocs", "Crocs"), ("timberland", "Timberland"), ("hoka", "Hoka"),
    ("salomon", "Salomon"), ("on running", "On"),
    # apparel / accessories
    ("fear of god", "Fear of God"), ("essentials", "Essentials"),
    ("the north face", "The North Face"), ("north face", "The North Face"),
    ("supreme", "Supreme"), ("new era", "New Era"), ("louis vuitton", "Louis Vuitton"),
    ("coach", "Coach"), ("vivienne westwood", "Vivienne Westwood"),
    ("abercrombie", "Abercrombie"), ("columbia", "Columbia"), ("champion", "Champion"),
    ("carhartt", "Carhartt"), ("lululemon", "Lululemon"), ("patagonia", "Patagonia"),
    ("ralph lauren", "Ralph Lauren"), ("polo", "Polo Ralph Lauren"),
    ("tommy hilfiger", "Tommy Hilfiger"), ("gucci", "Gucci"),
    # cards
    ("panini", "Panini"), ("prizm", "Panini"), ("nba hoops", "Panini"),
    ("hoops", "Panini"), ("select", "Panini"), ("optic", "Panini"),
    ("mosaic", "Panini"), ("chronicles", "Panini"), ("topps", "Topps"),
    ("bowman", "Bowman"), ("fleer", "Fleer"), ("upper deck", "Upper Deck"),
    ("donruss", "Donruss"),
]


def split_size_title(raw):
    m = (SIZE_SPACED_RE.match(raw or "")
         or SIZE_PARENDASH_RE.match(raw or "")
         or SIZE_NODASH_RE.match(raw or ""))
    if m:
        size = SIZE_NOISE_RE.sub("", m.group(1)).strip(" -,")
        return (size or None), m.group(2).strip()
    return None, (raw or "").strip()


def clean_title(name):
    t = (name or "").split(" | ")[0]                       # drop trailing style-code junk
    t = LEAD_JUNK_RE.sub("", t)                            # drop leading "CLEAN!-" etc.
    t = re.sub(r"\b(deadstock|rare)\b", "", t, flags=re.I)  # Josh: never use these words
    t = re.sub(r"\s{2,}", " ", t).strip(" -|·,")
    return t


def detect_brand(raw, fallback_name):
    low = (raw or "").lower()
    for needle, canon in BRAND_CANON:
        if needle in low:
            return canon
    # fallback: first real word of the product name, skipping leading years
    for w in (fallback_name or "").split():
        if not re.fullmatch(r"(19|20)\d{2}", w):
            return w.capitalize()
    return ""


SHOE_WORDS = ("shoe", "sneaker", "footwear", "cleat", "slide", "clog",
              "sandal", "boot", "loafer", "moccasin", "flip flop")


def category_for(leaf_name, title):
    """Classify from the most-specific (leaf) eBay category. Cards and shoes
    are detected explicitly; everything else (clothing, jerseys, hats,
    accessories, memorabilia) is Apparel."""
    leaf = (leaf_name or "").lower()
    t = (title or "").lower()
    if "card" in leaf:
        return "Cards"
    if any(w in leaf for w in SHOE_WORDS):
        return "Sneakers"
    # leaf occasionally generic; let an obvious shoe title still count
    if any(w in t for w in ("running shoes", "basketball shoes", "sneaker")):
        return "Sneakers"
    return "Apparel"


def normalize_condition(raw):
    c = (raw or "").strip()
    cl = c.lower()
    if "new" in cl:
        return "New"
    if cl in ("pre-owned", "preowned", "used", "very good", "good", "acceptable"):
        return "Used"
    return c or "Used"


def big_image(url):
    return re.sub(r"s-l\d+", "s-l960", url) if url else None


def collect_images(s):
    """All listing photos (main + extras), upscaled and de-duplicated."""
    urls = []
    main = (s.get("image") or {}).get("imageUrl")
    if main:
        urls.append(main)
    for im in (s.get("additionalImages") or []):
        u = im.get("imageUrl")
        if u:
            urls.append(u)
    seen, out = set(), []
    for u in urls:
        b = big_image(u)
        if b and b not in seen:
            seen.add(b)
            out.append(b)
    return out


def make_desc(category, condition):
    if category == "Cards":
        return f"{condition}. Priced fairly and shipped safely."
    if condition == "New":
        return "Brand new. Authenticated, fairly priced, and ready to ship."
    return "Pre-owned in great condition. Authenticated, fairly priced, and ready to ship."


def to_product(s):
    leaf = ""
    cats = s.get("categories") or []
    if cats:
        leaf = cats[0].get("categoryName", "")

    raw_title = s.get("title", "")
    size, name = split_size_title(raw_title)
    category = category_for(leaf, raw_title)
    title = clean_title(name)
    brand = detect_brand(raw_title, name)
    condition = normalize_condition(s.get("condition"))
    price = s.get("price") or {}
    images = collect_images(s)

    return {
        "id": s.get("itemId", ""),
        "title": title,
        "brand": brand,
        "category": category,
        "colorway": None,  # colour is already in the title
        "size": None if category == "Cards" else size,
        "condition": condition,
        "price": float(price.get("value", 0) or 0),
        "currency": price.get("currency", "USD"),
        "image": images[0] if images else None,
        "images": images,
        "ebayUrl": (s.get("itemWebUrl") or "https://www.ebay.com/").split("?")[0],
        "description": make_desc(category, condition),  # replaced with real eBay text in enrich step
    }


# ---------------------------------------------------------------- descriptions
def get_browse_remaining(token):
    """How many Browse API calls we have left today (None if unknown)."""
    try:
        r = urllib.request.Request(
            "https://api.ebay.com/developer/analytics/v1_beta/rate_limit/?api_context=buy&api_name=browse")
        r.add_header("Authorization", f"Bearer {token}")
        d = json.load(urllib.request.urlopen(r))
        for rl in d.get("rateLimits", []):
            for res in rl.get("resources", []):
                if res.get("name") == "buy.browse":
                    for rate in res.get("rates", []):
                        return rate.get("remaining")
    except Exception:
        pass
    return None


def fetch_description(token, item_id, marketplace):
    try:
        det = browse_get(f"/item/{urllib.parse.quote(item_id, safe='')}", token, marketplace)
        text = (det.get("shortDescription") or det.get("description") or "").strip()
        text = re.sub(r"<[^>]+>", " ", text)          # strip any HTML
        text = re.sub(r"\s+", " ", text).strip()
        return text or None
    except urllib.error.HTTPError:
        return None


def enrich_descriptions(products, token, marketplace):
    """Fill in real eBay descriptions, cached by item id so we only look up
    NEW items. A rate-limit guard keeps us from ever exhausting the daily quota."""
    cache_path = os.environ.get("DESC_CACHE", os.path.join(HERE, ".desc-cache.json"))
    cache = {}
    if os.path.exists(cache_path):
        try:
            cache = json.load(open(cache_path))
        except Exception:
            cache = {}

    need = [p for p in products if p["id"] not in cache]
    remaining = get_browse_remaining(token)
    budget = max(0, remaining - 500) if isinstance(remaining, int) else len(need)

    fetched = 0
    for p in need:
        if fetched >= budget:
            break
        desc = fetch_description(token, p["id"], marketplace)
        if desc:
            cache[p["id"]] = desc
            fetched += 1
        time.sleep(0.05)

    for p in products:
        if cache.get(p["id"]):
            p["description"] = cache[p["id"]]   # else keep the templated fallback

    current = {p["id"] for p in products}        # keep the cache lean
    cache = {k: v for k, v in cache.items() if k in current}
    try:
        os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
        json.dump(cache, open(cache_path, "w"))
    except Exception:
        pass

    have = sum(1 for p in products if cache.get(p["id"]))
    print(f"descriptions: {have}/{len(products)} have eBay text "
          f"({fetched} fetched this run; quota remaining ~{remaining})")


# ---------------------------------------------------------------- main
def main():
    cfg = load_config()
    print(f"Authenticating with eBay for seller '{cfg['sellerUsername']}'...")
    token = get_token(cfg["clientId"], cfg["clientSecret"])

    print("Fetching active listings...")
    summaries = search_seller_items(token, cfg["sellerUsername"], cfg["marketplace"], cfg["categoryIds"])
    # newest listings first, so the storefront leads with fresh inventory
    summaries.sort(key=lambda s: s.get("itemCreationDate", ""), reverse=True)
    products = [to_product(s) for s in summaries]
    # then lead with sneakers (the main line), then apparel, then cards;
    # stable sort keeps newest-first order within each group
    cat_rank = {"Sneakers": 0, "Apparel": 1, "Cards": 2}
    products.sort(key=lambda p: cat_rank.get(p["category"], 3))

    print("Filling in descriptions...")
    enrich_descriptions(products, token, cfg["marketplace"])

    out = {
        "updated": date.today().isoformat(),
        "note": "Generated automatically from The Wearforce eBay listings.",
        "items": products,
    }
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(out, f, indent=2)

    by_cat = {}
    for p in products:
        by_cat[p["category"]] = by_cat.get(p["category"], 0) + 1
    print(f"Wrote {len(products)} products to {OUTPUT_PATH}")
    print("By category:", dict(by_cat))


if __name__ == "__main__":
    main()
