from datetime import timezone

from bson import ObjectId
from flask import current_app
from pymongo import ReturnDocument
from werkzeug.security import generate_password_hash

from .db import collection, ensure_indexes
from .utils import as_utc, bson_size, idea_code, new_edit_token, sanitize_content, slugify, utcnow

CYCLE_NAME_PATTERN = r"^GRIT-Cycle[12]-\d{4}$"


def serialize_id(document):
    if not document:
        return None
    item = dict(document)
    item["_id"] = str(item["_id"])
    return item


def bootstrap_defaults():
    ensure_indexes()
    username = current_app.config.get("GIRT_BOOTSTRAP_CORE_USERNAME")
    password = current_app.config.get("GIRT_BOOTSTRAP_CORE_PASSWORD")
    name = current_app.config.get("GIRT_BOOTSTRAP_CORE_NAME", "Core Administrator")
    if username and password and not collection("users").find_one({"username": username}):
        create_user(username, name, password, "core")


def create_user(username, name, password, role):
    doc = {
        "username": username.strip().lower(),
        "name": name.strip(),
        "password_hash": generate_password_hash(password),
        "role": role,
        "active": True,
        "created_at": utcnow(),
    }
    result = collection("users").insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def upsert_seed_user(username, name, password, role):
    existing = collection("users").find_one({"username": username.strip().lower()})
    if existing:
        collection("users").update_one(
            {"_id": existing["_id"]},
            {"$set": {"name": name.strip(), "role": role, "active": True, "password_hash": generate_password_hash(password), "updated_at": utcnow()}},
        )
        return collection("users").find_one({"_id": existing["_id"]})
    return create_user(username, name, password, role)


def active_cycle(include_closed=False):
    now = utcnow()
    query = {"archived": {"$ne": True}}
    if not include_closed:
        query.update({"start_at": {"$lte": now}, "end_at": {"$gte": now}})
    return collection("cycles").find_one(query, sort=[("start_at", -1)])


def create_cycle(name, start_at, end_at):
    doc = {
        "name": name.strip(),
        "start_at": start_at.astimezone(timezone.utc),
        "end_at": end_at.astimezone(timezone.utc),
        "archived": False,
        "jury_released_at": None,
        "jury_closed_at": None,
        "created_at": utcnow(),
    }
    result = collection("cycles").insert_one(doc)
    doc["_id"] = result.inserted_id
    for name in current_app.config["DEFAULT_CATEGORIES"]:
        upsert_category(doc["_id"], name, 10)
    return doc


def cycle_name_is_valid(name):
    import re

    return bool(re.fullmatch(CYCLE_NAME_PATTERN, name.strip()))


def grit_cycle_name(cycle_number, year):
    cycle_number = str(cycle_number).strip()
    year = str(year).strip()
    candidate = f"GRIT-Cycle{cycle_number}-{year}"
    return candidate if cycle_name_is_valid(candidate) else None


def upsert_category(cycle_id, name, top_ideas_required, category_id=None):
    payload = {
        "cycle_id": str(cycle_id),
        "name": name.strip(),
        "slug": slugify(name),
        "top_ideas_required": max(1, int(top_ideas_required)),
        "active": True,
        "updated_at": utcnow(),
    }
    if category_id:
        return collection("categories").find_one_and_update(
            {"_id": ObjectId(category_id)},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
    payload.update({"jury_member_ids": [], "jury_lead_ids": [], "created_at": utcnow()})
    return collection("categories").find_one_and_update(
        {"cycle_id": str(cycle_id), "slug": payload["slug"]},
        {"$setOnInsert": payload},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def categories_for_cycle(cycle_id, active_only=True):
    query = {"cycle_id": str(cycle_id)}
    if active_only:
        query["active"] = True
    return list(collection("categories").find(query).sort("name", 1))


def cycle_is_open(cycle):
    now = utcnow()
    return bool(cycle and as_utc(cycle["start_at"]) <= now <= as_utc(cycle["end_at"]) and not cycle.get("archived"))


def cycle_accepts_jury(cycle):
    now = utcnow()
    return bool(
        cycle
        and cycle.get("jury_released_at")
        and not cycle.get("jury_closed_at")
        and now <= as_utc(cycle["end_at"])
        and not cycle.get("archived")
    )


def idea_payload(form, cycle, categories, attachments=None, existing=None):
    selected_category_ids = form.getlist("category_ids") if hasattr(form, "getlist") else form.get("category_ids", [])
    valid_category_ids = {str(category["_id"]) for category in categories}
    selected_category_ids = [value for value in selected_category_ids if value in valid_category_ids][:2]
    contributors = []
    for index in range(1, 6):
        name = form.get(f"contributor_name_{index}", "").strip()
        username = form.get(f"contributor_username_{index}", "").strip()
        if name or username:
            contributors.append({"name": name, "username": username})
    payload = {
        "cycle_id": str(cycle["_id"]),
        "problem_statement": form.get("problem_statement", "").strip(),
        "solution_summary": form.get("solution_summary", "").strip(),
        "video_link": form.get("video_link", "").strip(),
        "can_be_patented": bool(form.get("can_be_patented")),
        "is_patented": bool(form.get("is_patented")),
        "production_readiness": form.get("production_readiness", ""),
        "contributors": contributors,
        "team_name": form.get("team_name", "").strip(),
        "officer_sponsor": form.get("officer_sponsor", "").strip(),
        "content_format": form.get("content_format", "plain"),
        "content": sanitize_content(form.get("content", ""), form.get("content_format", "plain")),
        "category_ids": selected_category_ids,
        "owner_name": form.get("owner_name", "").strip(),
        "owner_employee_id": form.get("owner_employee_id", "").strip().upper(),
        "office_location": form.get("office_location", "").strip(),
        "india_region": form.get("india_region", "").strip(),
        "updated_at": utcnow(),
    }
    payload["attachments"] = list(existing.get("attachments", [])) if existing else []
    payload["attachments"].extend(attachments or [])
    return payload


def validate_idea(payload):
    errors = []
    required_fields = {
        "problem_statement": "Problem statement",
        "solution_summary": "Solution",
        "production_readiness": "Deployed on PROD",
        "officer_sponsor": "Officer sponsor",
        "owner_name": "Submitter FTE name",
        "owner_employee_id": "Employee ID",
        "office_location": "Office location",
        "india_region": "Country",
        "content": "Solution content",
    }
    for field, label in required_fields.items():
        if not payload.get(field):
            errors.append(f"{label} is required.")
    if not payload.get("contributors"):
        errors.append("Add at least one contributor.")
    if len(payload.get("category_ids", [])) not in {1, 2}:
        errors.append("Select one or two categories.")
    if payload.get("production_readiness") not in {"yes", "no", "in_6_months"}:
        errors.append("Deployed on PROD must be yes, no, or planned in 6 months.")
    if payload.get("office_location") not in current_app.config["OFFICE_LOCATIONS"]:
        errors.append("Office location must be Mumbai or Bangalore.")
    if payload.get("india_region") != "India":
        errors.append("Country must be India.")
    if bson_size(payload) >= current_app.config["MAX_BSON_BYTES"]:
        errors.append("The idea content is too large for a MongoDB document. Reduce text or attachments.")
    return errors


def create_idea(form, cycle, categories, attachments):
    payload = idea_payload(form, cycle, categories, attachments)
    errors = validate_idea(payload)
    edit_pin = form.get("edit_pin", "").strip()
    if len(edit_pin) < 8:
        errors.append("Create an edit passcode of at least eight characters.")
    if errors:
        return None, errors
    payload["edit_pin_hash"] = generate_password_hash(edit_pin)
    payload.update(
        {
            "idea_id": idea_code(cycle["name"]),
            "edit_token": new_edit_token(),
            "archived": False,
            "created_at": utcnow(),
        }
    )
    result = collection("ideas").insert_one(payload)
    payload["_id"] = result.inserted_id
    return payload, []


def update_idea(existing, form, cycle, categories, attachments):
    payload = idea_payload(form, cycle, categories, attachments, existing)
    errors = validate_idea(payload)
    if errors:
        return None, errors
    collection("ideas").update_one({"_id": existing["_id"]}, {"$set": payload})
    existing.update(payload)
    return existing, []


def score_summary(idea_id, category_id=None):
    query = {"idea_id": idea_id}
    if category_id:
        query["category_id"] = str(category_id)
    rows = list(collection("evaluations").find(query))
    scores = [row["score"] for row in rows if row.get("score")]
    return {
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "score_count": len(scores),
        "evaluations": rows,
    }


def ideas_with_scores(ideas, category_id=None):
    records = []
    for idea in ideas:
        record = dict(idea)
        record.update(score_summary(idea["idea_id"], category_id))
        records.append(record)
    return sorted(records, key=lambda item: item["average_score"], reverse=True)
