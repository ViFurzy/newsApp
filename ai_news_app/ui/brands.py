"""
ui/brands.py — Find the company a headline is about and draw a logo card for it.

Pure functions, no network (main.py fetches the logo). Logos are Simple Icons paths
(24x24 viewBox); brands Simple Icons dropped (Amazon, OpenAI, Microsoft...) get a wordmark card.
"""
import re
from html import escape

# (pattern, label, Simple Icons slug or None). Case-sensitive on purpose: "Apple" the company, not the fruit.
_BRANDS = [
    (r"Meta|Facebook", "Meta", "meta"),
    (r"Instagram", "Instagram", "instagram"),
    (r"WhatsApp", "WhatsApp", "whatsapp"),
    (r"Google|Gemini|DeepMind", "Google", "google"),
    (r"OpenAI|ChatGPT", "OpenAI", None),
    (r"Anthropic|Claude", "Anthropic", "anthropic"),
    (r"Microsoft|Copilot", "Microsoft", None),
    (r"Amazon|AWS", "Amazon", None),
    (r"Apple|iPhone", "Apple", "apple"),
    (r"Nvidia|NVIDIA", "Nvidia", "nvidia"),
    (r"Huawei", "Huawei", "huawei"),
    (r"Samsung", "Samsung", "samsung"),
    (r"Xiaomi", "Xiaomi", "xiaomi"),
    (r"Intel", "Intel", "intel"),
    (r"AMD", "AMD", "amd"),
    (r"Qualcomm", "Qualcomm", "qualcomm"),
    (r"Tesla", "Tesla", "tesla"),
    (r"SpaceX", "SpaceX", "spacex"),
    (r"xAI|Grok", "xAI", None),
    (r"DeepSeek", "DeepSeek", "deepseek"),
    (r"Mistral", "Mistral", "mistralai"),
    (r"Perplexity", "Perplexity", "perplexity"),
    (r"TikTok|ByteDance", "TikTok", "tiktok"),
    (r"Alibaba|Qwen", "Alibaba", "alibabadotcom"),
    (r"Baidu", "Baidu", "baidu"),
    (r"GitHub", "GitHub", "github"),
    (r"Hugging Face", "Hugging Face", "huggingface"),
    (r"Cursor", "Cursor", "cursor"),
    (r"Netflix", "Netflix", "netflix"),
    (r"Spotify", "Spotify", "spotify"),
    (r"Uber", "Uber", "uber"),
    (r"Stripe", "Stripe", "stripe"),
    (r"Shopify", "Shopify", "shopify"),
    (r"Walmart", "Walmart", None),
    (r"Salesforce", "Salesforce", None),
    (r"IBM", "IBM", None),
    (r"Oracle", "Oracle", None),
    (r"Adobe", "Adobe", None),
    (r"TechCrunch", "TechCrunch", "techcrunch"),
    (r"PHP", "PHP", "php"),
    (r"Linux", "Linux", "linux"),
    (r"Android", "Android", "android"),
]
_COMPILED = [(re.compile(rf"\b(?:{p})\b"), label, slug) for p, label, slug in _BRANDS]


def find_brand(title: str):
    """(label, slug) of the brand named first in the title, or None."""
    hits = [(m.start(), label, slug) for rx, label, slug in _COMPILED if (m := rx.search(title))]
    if not hits:
        return None
    _, label, slug = min(hits, key=lambda h: h[0])
    return label, slug


def brand_filename(label: str) -> str:
    return "brand-" + re.sub(r"[^a-z0-9]+", "", label.lower()) + ".svg"


def logo_paths(simple_icons_svg: str) -> list:
    """Only the path data is kept — never embed a remote SVG wholesale."""
    return re.findall(r'<path d="([^"]+)"', simple_icons_svg)


def card_svg(label: str, paths: list) -> str:
    """16:9 dark card (matches the theme) with the logo + label; wordmark only when there is no logo.
    Content stays in the middle band, since cards crop the image to a wide strip."""
    head = ('<svg xmlns="http://www.w3.org/2000/svg" width="720" height="405" viewBox="0 0 720 405">'
            '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#14171f"/><stop offset="1" stop-color="#262b3b"/>'
            '</linearGradient></defs><rect width="720" height="405" fill="url(#g)"/>')
    if paths:
        body = ('<g transform="translate(305 106) scale(4.6)" fill="#f0ece4">'
                + "".join(f'<path d="{escape(d)}"/>' for d in paths) + '</g>'
                f'<text x="360" y="276" text-anchor="middle" font-family="ui-monospace,Consolas,monospace" '
                f'font-size="24" letter-spacing="7" fill="#c87038">{escape(label.upper())}</text>')
    else:
        size = min(72, 640 * 1.6 / len(label))
        body = (f'<text x="360" y="222" text-anchor="middle" font-family="Georgia,serif" font-weight="700" '
                f'font-size="{size:.0f}" fill="#f0ece4">{escape(label)}</text>'
                '<rect x="320" y="250" width="80" height="3" fill="#c87038"/>')
    return head + body + "</svg>"
