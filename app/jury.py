from bson import ObjectId
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from .db import collection
from .entitlements import is_assigned_to_category, is_idea_contributor, require_category_assignment, require_screen
from .services import cycle_accepts_jury, ideas_with_scores
from .utils import paged, utcnow


jury_bp = Blueprint("jury", __name__, url_prefix="/jury")


def assigned_categories():
    cycle = collection("cycles").find_one({"archived": {"$ne": True}}, sort=[("start_at", -1)])
    if not cycle:
        return []
    base_query = {"active": True, "cycle_id": str(cycle["_id"])}
    if g.user["role"] == "core":
        return list(collection("categories").find(base_query).sort("name", 1))
    juror_id = str(g.user["_id"])
    base_query["$or"] = [{"jury_member_ids": juror_id}, {"jury_lead_ids": juror_id}]
    return list(
        collection("categories").find(base_query).sort("name", 1)
    )


def category_context(category_id=None):
    categories = assigned_categories()
    category = next((item for item in categories if str(item["_id"]) == category_id), categories[0] if categories else None)
    cycle = collection("cycles").find_one({"_id": ObjectId(category["cycle_id"])}) if category else None
    return categories, category, cycle


def evaluation_status_for(user, category, ideas):
    idea_ids = [idea["idea_id"] for idea in ideas]
    rows = list(
        collection("evaluations").find(
            {"idea_id": {"$in": idea_ids}, "category_id": str(category["_id"]), "juror_id": str(user["_id"])}
        )
    ) if idea_ids else []
    scored_map = {row["idea_id"]: row for row in rows}
    for idea in ideas:
        idea["my_evaluation"] = scored_map.get(idea["idea_id"])
        idea["review_status"] = "scored" if idea["idea_id"] in scored_map else "pending"
    return scored_map


def attach_peer_evaluations(category, ideas):
    idea_ids = [idea["idea_id"] for idea in ideas]
    rows = list(
        collection("evaluations")
        .find({"idea_id": {"$in": idea_ids}, "category_id": str(category["_id"])})
        .sort("updated_at", -1)
    ) if idea_ids else []
    grouped = {}
    for row in rows:
        grouped.setdefault(row["idea_id"], []).append(row)
    for idea in ideas:
        idea["peer_evaluations"] = grouped.get(idea["idea_id"], [])


@jury_bp.get("/")
@require_screen("jury")
def dashboard():
    categories, category, cycle = category_context(request.args.get("category_id"))
    page = int(request.args.get("page", 1))
    ideas = []
    total = 0
    scored_total = 0
    pending_total = 0
    is_lead = bool(category and is_assigned_to_category(g.user, category, lead_only=True))
    if category and cycle_accepts_jury(cycle):
        query = {"cycle_id": str(cycle["_id"]), "category_ids": str(category["_id"]), "archived": {"$ne": True}}
        total = collection("ideas").count_documents(query)
        category_idea_ids = [row["idea_id"] for row in collection("ideas").find(query, {"idea_id": 1})]
        scored_total = collection("evaluations").count_documents(
            {"idea_id": {"$in": category_idea_ids}, "category_id": str(category["_id"]), "juror_id": str(g.user["_id"])}
        ) if category_idea_ids else 0
        pending_total = max(total - scored_total, 0)
        ideas = ideas_with_scores(
            list(paged(collection("ideas").find(query), page, current_app.config["PER_PAGE"])),
            str(category["_id"]),
        )
        evaluation_status_for(g.user, category, ideas)
        if is_lead:
            attach_peer_evaluations(category, ideas)
    return render_template(
        "jury/dashboard.html",
        categories=categories,
        category=category,
        cycle=cycle,
        cycle_accepts_jury=cycle_accepts_jury(cycle),
        ideas=ideas,
        total=total,
        page=page,
        per_page=current_app.config["PER_PAGE"],
        is_lead=is_lead,
        scored_total=scored_total,
        pending_total=pending_total,
    )


@jury_bp.route("/ideas/<idea_id>", methods=["GET", "POST"])
@require_screen("jury")
def idea(idea_id):
    idea = collection("ideas").find_one({"idea_id": idea_id, "archived": {"$ne": True}})
    if not idea:
        abort(404, "Idea not found.")
    category = collection("categories").find_one({"_id": ObjectId(request.args.get("category_id") or idea["category_ids"][0])})
    cycle = collection("cycles").find_one({"_id": ObjectId(idea["cycle_id"])})
    require_category_assignment(category)
    if not cycle_accepts_jury(cycle):
        abort(403, "The jury review window is closed.")
    self_review = is_idea_contributor(g.user, idea)
    evaluation = collection("evaluations").find_one(
        {"idea_id": idea_id, "category_id": str(category["_id"]), "juror_id": str(g.user["_id"])}
    )
    if request.method == "POST":
        if self_review:
            abort(403, "Jury members cannot score ideas they contributed to.")
        score = int(request.form.get("score", 0))
        if score not in range(1, 11):
            flash("Score must be between 1 and 10.", "error")
        else:
            collection("evaluations").update_one(
                {"idea_id": idea_id, "category_id": str(category["_id"]), "juror_id": str(g.user["_id"])},
                {"$set": {
                    "category_id": str(category["_id"]),
                    "score": score,
                    "comment": request.form.get("comment", "").strip(),
                    "sentiment": request.form.get("sentiment", "neutral"),
                    "juror_name": g.user["name"],
                    "updated_at": utcnow(),
                }, "$setOnInsert": {"created_at": utcnow()}},
                upsert=True,
            )
            flash("Evaluation saved.", "success")
            return redirect(url_for("jury.idea", idea_id=idea_id, category_id=str(category["_id"])))
        evaluation = {"score": score, "comment": request.form.get("comment", ""), "sentiment": request.form.get("sentiment", "neutral")}
    is_lead = is_assigned_to_category(g.user, category, lead_only=True)
    peer_evaluations = []
    if is_lead:
        peer_evaluations = list(
            collection("evaluations")
            .find({"idea_id": idea_id, "category_id": str(category["_id"])})
            .sort("updated_at", -1)
        )
    return render_template(
        "jury/idea.html",
        idea=idea,
        category=category,
        cycle=cycle,
        evaluation=evaluation,
        is_lead=is_lead,
        peer_evaluations=peer_evaluations,
        self_review=self_review,
    )


@jury_bp.post("/ideas/<idea_id>/lead-comment")
@require_screen("jury")
def lead_comment(idea_id):
    idea = collection("ideas").find_one({"idea_id": idea_id})
    category = collection("categories").find_one({"_id": ObjectId(request.form.get("category_id"))})
    require_category_assignment(category, lead_only=True)
    if is_idea_contributor(g.user, idea):
        abort(403, "Jury leads cannot add winner comments to ideas they contributed to.")
    collection("ideas").update_one(
        {"_id": idea["_id"]},
        {"$set": {f"lead_comments.{str(category['_id'])}": request.form.get("lead_comment", "").strip(), "updated_at": utcnow()}},
    )
    flash("Jury lead comment saved.", "success")
    return redirect(url_for("jury.idea", idea_id=idea_id, category_id=str(category["_id"])))


@jury_bp.post("/categories/<category_id>/confirm")
@require_screen("jury")
def confirm_winners(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    require_category_assignment(category, lead_only=True)
    cycle = collection("cycles").find_one({"_id": ObjectId(category["cycle_id"])})
    if not cycle_accepts_jury(cycle):
        abort(403, "The jury review window is closed.")
    ideas = ideas_with_scores(
        list(collection("ideas").find({"cycle_id": str(cycle["_id"]), "category_ids": str(category["_id"]), "archived": {"$ne": True}})),
        str(category["_id"]),
    )
    winner_ids = [idea["idea_id"] for idea in ideas[: category.get("top_ideas_required", 10)]]
    collection("categories").update_one(
        {"_id": category["_id"]},
        {"$set": {"winner_ids": winner_ids, "winners_confirmed_at": utcnow(), "confirmed_by": str(g.user["_id"])}},
    )
    flash("Top ideas confirmed for the core committee.", "success")
    return redirect(url_for("jury.dashboard", category_id=category_id))
