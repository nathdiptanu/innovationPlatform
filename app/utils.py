import re
import secrets
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

from bson import BSON
from flask import current_app
from werkzeug.utils import secure_filename


HTML_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "h2",
    "h3",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
HTML_ATTRIBUTES = {"a": ["href", "title", "target"], "th": ["colspan"], "td": ["colspan"]}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


class AllowedHTMLCleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in HTML_TAGS:
            return
        allowed_attrs = []
        for name, value in attrs:
            if name not in HTML_ATTRIBUTES.get(tag, []):
                continue
            if name == "href" and value and not value.lower().startswith(("http://", "https://", "mailto:")):
                continue
            allowed_attrs.append(f'{name}="{escape(value or "", quote=True)}"')
        attributes = f" {' '.join(allowed_attrs)}" if allowed_attrs else ""
        self.parts.append(f"<{tag}{attributes}>")

    def handle_endtag(self, tag):
        if tag in HTML_TAGS and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(escape(data))


def clean_html(content):
    cleaner = AllowedHTMLCleaner()
    cleaner.feed(content)
    cleaner.close()
    return "".join(cleaner.parts)


def utcnow():
    return datetime.now(timezone.utc)


def as_utc(value):
    if not value:
        return value
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def parse_datetime(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def sanitize_content(content, content_format):
    if content_format == "html":
        return clean_html(content)
    return content.strip()


def bson_size(document):
    return len(BSON.encode(document))


def paged(cursor, page, per_page):
    page = max(page, 1)
    return cursor.skip((page - 1) * per_page).limit(per_page)


def idea_code(cycle_name):
    cycle_fragment = re.sub(r"[^A-Za-z0-9-]+", "-", cycle_name.strip()).strip("-")
    return f"{cycle_fragment}-{uuid4().hex[:8].upper()}"


def new_edit_token():
    return secrets.token_urlsafe(24)


def save_images(files, display_names=None):
    saved = []
    display_names = display_names or []
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    upload_root.mkdir(parents=True, exist_ok=True)
    for index, file in enumerate(files):
        filename = secure_filename(file.filename or "")
        if not filename or "." not in filename:
            continue
        extension = filename.rsplit(".", 1)[1].lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            continue
        stored_name = f"{uuid4().hex}.{extension}"
        file.save(upload_root / stored_name)
        saved.append({
            "original_name": filename,
            "display_name": (display_names[index].strip() if index < len(display_names) else "") or filename,
            "path": f"uploads/{stored_name}",
        })
    return saved
