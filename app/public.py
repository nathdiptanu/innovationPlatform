import re
from uuid import uuid4

from bson import ObjectId
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import collection
from .services import active_cycle, categories_for_cycle, create_idea, cycle_is_open, update_idea
from .utils import paged, save_images
from .utils import utcnow


public_bp = Blueprint("public", __name__)

IDEA_LIST_FIELDS = {
    "idea_id": 1,
    "problem_statement": 1,
    "solution_summary": 1,
    "owner_name": 1,
    "office_location": 1,
    "india_region": 1,
    "category_ids": 1,
    "production_readiness": 1,
    "reaction_counts": 1,
    "updated_at": 1,
    "created_at": 1,
}


def image_display_names(form):
    return [line.strip() for line in form.get("image_names", "").splitlines()]


def visitor_id():
    if "visitor_id" not in session:
        session["visitor_id"] = uuid4().hex
    return session["visitor_id"]


def owns_edit_session(idea):
    session_token = session.get(f"edit:{idea['idea_id']}")
    submitter_visitor_id = idea.get("submitter_visitor_id")
    visitor_matches = not submitter_visitor_id or submitter_visitor_id == visitor_id()
    return bool(session_token and session_token == idea.get("edit_token") and visitor_matches)


def unlock_edit_session(idea):
    supplied_employee_id = (request.values.get("owner_employee_id") or "").strip().upper()
    supplied_pin = (request.values.get("edit_pin") or "").strip()
    pin_hash = idea.get("edit_pin_hash")
    if supplied_employee_id == idea.get("owner_employee_id") and pin_hash and check_password_hash(pin_hash, supplied_pin):
        current_visitor = visitor_id()
        session[f"edit:{idea['idea_id']}"] = idea["edit_token"]
        collection("ideas").update_one(
            {"_id": idea["_id"]},
            {"$set": {"submitter_visitor_id": current_visitor, "updated_at": utcnow()}},
        )
        idea["submitter_visitor_id"] = current_visitor
        return True
    return False


def search_query(cycle, text, category_id=None):
    query = {"archived": {"$ne": True}}
    if cycle:
        query["cycle_id"] = str(cycle["_id"])
    if category_id:
        query["category_ids"] = category_id
    if text:
        text = re.escape(text)
        query["$or"] = [
            {"idea_id": {"$regex": text, "$options": "i"}},
            {"problem_statement": {"$regex": text, "$options": "i"}},
            {"solution_summary": {"$regex": text, "$options": "i"}},
            {"owner_name": {"$regex": text, "$options": "i"}},
            {"owner_employee_id": {"$regex": text, "$options": "i"}},
            {"team_name": {"$regex": text, "$options": "i"}},
        ]
    return query


@public_bp.get("/")
def home():
    cycle = active_cycle(include_closed=True)
    page = int(request.args.get("page", 1))
    q = request.args.get("q", "").strip()
    categories = categories_for_cycle(cycle["_id"]) if cycle else []
    category_map = {str(category["_id"]): category for category in categories}
    selected_category_id = request.args.get("category_id", "").strip()
    if selected_category_id not in category_map:
        selected_category_id = ""
    query = search_query(cycle, q, selected_category_id)
    cursor = collection("ideas").find(query, IDEA_LIST_FIELDS).sort("created_at", -1)
    total = collection("ideas").count_documents(query)
    total_so_far = collection("ideas").count_documents(
        {"cycle_id": str(cycle["_id"]), "archived": {"$ne": True}}
    ) if cycle else 0
    ideas = list(paged(cursor, page, current_app.config["PER_PAGE"]))
    return render_template(
        "public/home.html",
        cycle=cycle,
        cycle_open=cycle_is_open(cycle),
        ideas=ideas,
        category_tabs=categories,
        categories=category_map,
        selected_category_id=selected_category_id,
        q=q,
        page=page,
        total=total,
        total_so_far=total_so_far,
        per_page=current_app.config["PER_PAGE"],
    )


@public_bp.get("/users/")
def user_portal():
    return home()


@public_bp.route("/ideas/new", methods=["GET", "POST"])
def create():
    cycle = active_cycle(include_closed=True)
    if not cycle or not cycle_is_open(cycle):
        flash("Submissions are closed for the current cycle.", "error")
        return redirect(url_for("public.home"))
    categories = categories_for_cycle(cycle["_id"])
    if request.method == "POST":
        idea, errors = create_idea(
            request.form,
            cycle,
            categories,
            save_images(request.files.getlist("images"), image_display_names(request.form)),
        )
        if not errors:
            submitter_id = visitor_id()
            collection("ideas").update_one({"_id": idea["_id"]}, {"$set": {"submitter_visitor_id": submitter_id, "updated_at": utcnow()}})
            idea["submitter_visitor_id"] = submitter_id
            session[f"edit:{idea['idea_id']}"] = idea["edit_token"]
            flash(f"Idea {idea['idea_id']} submitted. Keep your Employee ID and private edit passcode to edit it later.", "success")
            return redirect(url_for("public.idea_detail", idea_id=idea["idea_id"]))
        for error in errors:
            flash(error, "error")
    return render_template("public/idea_form.html", cycle=cycle, categories=categories, idea=None)


@public_bp.get("/ideas/<idea_id>")
def idea_detail(idea_id):
    idea = collection("ideas").find_one({"idea_id": idea_id, "archived": {"$ne": True}})
    if not idea:
        abort(404, "Idea not found.")
    cycle = collection("cycles").find_one({"_id": ObjectId(idea["cycle_id"])})
    categories = categories_for_cycle(cycle["_id"], active_only=False)
    edit_allowed = not cycle.get("archived")
    can_edit = edit_allowed and owns_edit_session(idea)
    return render_template(
        "public/idea_detail.html",
        idea=idea,
        cycle=cycle,
        can_edit=can_edit,
        edit_allowed=edit_allowed,
        visitor_reaction=collection("idea_reactions").find_one({"idea_id": idea_id, "visitor_id": visitor_id()}),
        categories={str(category["_id"]): category for category in categories},
    )


@public_bp.post("/ideas/<idea_id>/comments")
def add_comment(idea_id):
    idea = collection("ideas").find_one({"idea_id": idea_id, "archived": {"$ne": True}})
    if not idea:
        abort(404, "Idea not found.")
    name = request.form.get("commenter_name", "").strip()
    comment = request.form.get("comment", "").strip()
    sentiment = request.form.get("sentiment", "neutral")
    if sentiment not in {"like", "neutral", "dislike"}:
        sentiment = "neutral"
    if not name or not comment:
        flash("Add your name and comment before posting feedback.", "error")
    else:
        collection("ideas").update_one(
            {"_id": idea["_id"]},
            {"$push": {"public_comments": {
                "name": name,
                "username": request.form.get("commenter_username", "").strip(),
                "comment": comment,
                "sentiment": sentiment,
                "created_at": utcnow(),
            }}, "$set": {"updated_at": utcnow()}},
        )
        flash("Feedback added.", "success")
    return redirect(url_for("public.idea_detail", idea_id=idea_id))


@public_bp.post("/ideas/<idea_id>/react")
def react(idea_id):
    idea = collection("ideas").find_one({"idea_id": idea_id, "archived": {"$ne": True}})
    if not idea:
        abort(404, "Idea not found.")
    sentiment = request.form.get("sentiment", "neutral")
    if sentiment not in {"like", "neutral", "dislike"}:
        abort(400, "Invalid reaction.")
    visitor = visitor_id()
    existing = collection("idea_reactions").find_one({"idea_id": idea_id, "visitor_id": visitor})
    if existing and existing.get("sentiment") == sentiment:
        flash("Your reaction is already saved.", "success")
        return redirect(url_for("public.idea_detail", idea_id=idea_id))
    inc = {f"reaction_counts.{sentiment}": 1}
    if existing:
        inc[f"reaction_counts.{existing['sentiment']}"] = -1
    collection("idea_reactions").update_one(
        {"idea_id": idea_id, "visitor_id": visitor},
        {"$set": {"sentiment": sentiment, "updated_at": utcnow()}, "$setOnInsert": {"created_at": utcnow()}},
        upsert=True,
    )
    collection("ideas").update_one({"_id": idea["_id"]}, {"$inc": inc, "$set": {"updated_at": utcnow()}})
    flash("Reaction saved.", "success")
    return redirect(url_for("public.idea_detail", idea_id=idea_id))


@public_bp.route("/ideas/<idea_id>/edit", methods=["GET", "POST"])
def edit(idea_id):
    idea = collection("ideas").find_one({"idea_id": idea_id, "archived": {"$ne": True}})
    if not idea:
        abort(404, "Idea not found.")
    cycle = collection("cycles").find_one({"_id": ObjectId(idea["cycle_id"])})
    token = request.args.get("token") or request.form.get("token") or session.get(f"edit:{idea_id}")
    if not owns_edit_session(idea):
        if unlock_edit_session(idea):
            flash("Edit access restored for this browser session.", "success")
            return redirect(url_for("public.edit", idea_id=idea_id))
        if request.method == "POST" and request.form.get("unlock_edit"):
            flash("Employee ID or private passcode did not match this idea.", "error")
        return render_template("public/edit_unlock.html", idea=idea), 403
    if cycle.get("jury_released_at") or cycle.get("archived"):
        flash("This idea is locked because it has been released to jury or archived.", "error")
        return redirect(url_for("public.idea_detail", idea_id=idea_id))
    categories = categories_for_cycle(cycle["_id"])
    if request.method == "POST":
        updated, errors = update_idea(
            idea,
            request.form,
            cycle,
            categories,
            save_images(request.files.getlist("images"), image_display_names(request.form)),
        )
        if not errors:
            flash("Idea updated.", "success")
            return redirect(url_for("public.idea_detail", idea_id=idea_id, token=token))
        for error in errors:
            flash(error, "error")
        idea = updated or idea
    return render_template("public/idea_form.html", cycle=cycle, categories=categories, idea=idea, token=token)
