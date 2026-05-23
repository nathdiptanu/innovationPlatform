import re

from bson import ObjectId
from flask import Blueprint, abort, current_app, jsonify, render_template, request, url_for
from werkzeug.datastructures import MultiDict

from .db import collection
from .entitlements import can_access, load_current_user, require_screen
from .openapi import build_openapi
from .services import active_cycle, categories_for_cycle, create_idea, cycle_is_open, serialize_id, update_idea
from .utils import paged


api_bp = Blueprint("api", __name__, url_prefix="/api")


def json_form(data):
    form = MultiDict()
    for key, value in data.items():
        if key == "contributors":
            for index, contributor in enumerate(value[:5], start=1):
                form.add(f"contributor_name_{index}", contributor.get("name", ""))
                form.add(f"contributor_username_{index}", contributor.get("username", ""))
        elif isinstance(value, list):
            for item in value:
                form.add(key, item)
        elif isinstance(value, bool):
            if value:
                form.add(key, "on")
        else:
            form.add(key, value)
    return form


def idea_json(idea):
    item = serialize_id(idea)
    item.pop("edit_token", None)
    return item


@api_bp.get("/docs")
@require_screen("core")
def docs():
    return render_template("swagger.html")


@api_bp.get("/openapi.json")
@require_screen("core")
def openapi():
    return jsonify(build_openapi())


@api_bp.get("/cycles/current")
def current_cycle():
    cycle = active_cycle(include_closed=True)
    if not cycle:
        return jsonify(None)
    return jsonify({"id": str(cycle["_id"]), "name": cycle["name"], "start_at": cycle["start_at"], "end_at": cycle["end_at"], "submission_open": cycle_is_open(cycle)})


@api_bp.get("/categories")
def categories():
    cycle = active_cycle(include_closed=True)
    return jsonify([{"id": str(category["_id"]), "name": category["name"], "top_ideas_required": category["top_ideas_required"]} for category in categories_for_cycle(cycle["_id"])] if cycle else [])


@api_bp.route("/ideas", methods=["GET", "POST"])
def ideas():
    cycle = active_cycle(include_closed=True)
    if request.method == "GET":
        q = request.args.get("q", "").strip()
        page = max(int(request.args.get("page", 1)), 1)
        query = {"archived": {"$ne": True}}
        if cycle:
            query["cycle_id"] = str(cycle["_id"])
        if q:
            q = re.escape(q)
            query["$or"] = [{"idea_id": {"$regex": q, "$options": "i"}}, {"problem_statement": {"$regex": q, "$options": "i"}}, {"owner_employee_id": {"$regex": q, "$options": "i"}}]
        total = collection("ideas").count_documents(query)
        rows = list(paged(collection("ideas").find(query).sort("created_at", -1), page, current_app.config["PER_PAGE"]))
        return jsonify({"items": [idea_json(row) for row in rows], "page": page, "total": total})
    if not cycle or not cycle_is_open(cycle):
        return jsonify({"error": "Submission window closed."}), 409
    idea, errors = create_idea(json_form(request.get_json(silent=True) or {}), cycle, categories_for_cycle(cycle["_id"]), [])
    if errors:
        return jsonify({"errors": errors}), 400
    return jsonify({"idea_id": idea["idea_id"], "edit_token": idea["edit_token"], "edit_url": url_for("public.edit", idea_id=idea["idea_id"], token=idea["edit_token"], _external=True)}), 201


@api_bp.route("/ideas/<idea_id>", methods=["GET", "PUT"])
def idea(idea_id):
    idea = collection("ideas").find_one({"idea_id": idea_id, "archived": {"$ne": True}})
    if not idea:
        abort(404, "Idea not found.")
    cycle = collection("cycles").find_one({"_id": ObjectId(idea["cycle_id"])})
    if request.method == "GET":
        return jsonify(idea_json(idea))
    if request.headers.get("X-Edit-Token") != idea.get("edit_token"):
        return jsonify({"error": "Invalid edit token."}), 403
    if not cycle_is_open(cycle):
        return jsonify({"error": "Cycle closed."}), 409
    updated, errors = update_idea(idea, json_form(request.get_json(silent=True) or {}), cycle, categories_for_cycle(cycle["_id"]), [])
    if errors:
        return jsonify({"errors": errors}), 400
    return jsonify(idea_json(updated))


@api_bp.get("/core/dashboard")
def core_dashboard():
    user = load_current_user()
    if not can_access("core", user):
        return jsonify({"error": "Core access required."}), 403
    cycle = active_cycle(include_closed=True)
    if not cycle:
        return jsonify({"cycle": None, "counts": []})
    categories = categories_for_cycle(cycle["_id"], active_only=False)
    return jsonify({
        "cycle": {"id": str(cycle["_id"]), "name": cycle["name"]},
        "counts": [{"category_id": str(category["_id"]), "name": category["name"], "ideas": collection("ideas").count_documents({"cycle_id": str(cycle["_id"]), "category_ids": str(category["_id"]), "archived": {"$ne": True}})} for category in categories],
    })
