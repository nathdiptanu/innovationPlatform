from datetime import datetime

from bson import ObjectId
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from .db import collection
from .entitlements import require_screen
from .services import categories_for_cycle, create_cycle, create_user, grit_cycle_name, ideas_with_scores, upsert_category
from .utils import paged, parse_datetime, utcnow


core_bp = Blueprint("core", __name__, url_prefix="/core")


def selected_cycle():
    cycle_id = request.args.get("cycle_id") or request.form.get("cycle_id")
    if cycle_id:
        return collection("cycles").find_one({"_id": ObjectId(cycle_id)})
    return collection("cycles").find_one({"archived": {"$ne": True}}, sort=[("start_at", -1)])


@core_bp.get("/")
@require_screen("core")
def dashboard():
    cycle = selected_cycle()
    categories = categories_for_cycle(cycle["_id"], active_only=False) if cycle else []
    selected_category_id = request.args.get("category_id") or (str(categories[0]["_id"]) if categories else None)
    page = int(request.args.get("page", 1))
    category_counts = {
        str(category["_id"]): collection("ideas").count_documents(
            {"cycle_id": str(cycle["_id"]), "category_ids": str(category["_id"]), "archived": {"$ne": True}}
        )
        for category in categories
    } if cycle else {}
    cycle_total = collection("ideas").count_documents(
        {"cycle_id": str(cycle["_id"]), "archived": {"$ne": True}}
    ) if cycle else 0
    ideas_query = {"cycle_id": str(cycle["_id"]), "archived": {"$ne": True}} if cycle else {}
    if selected_category_id:
        ideas_query["category_ids"] = selected_category_id
    total = collection("ideas").count_documents(ideas_query) if cycle else 0
    cursor = collection("ideas").find(ideas_query).sort("created_at", -1) if cycle else []
    ideas = list(paged(cursor, page, current_app.config["PER_PAGE"])) if cycle else []
    selected_category = next((category for category in categories if str(category["_id"]) == selected_category_id), None)
    confirmed_ideas = []
    if selected_category and selected_category.get("winner_ids"):
        confirmed_map = {
            idea["idea_id"]: idea
            for idea in ideas_with_scores(list(collection("ideas").find({"idea_id": {"$in": selected_category["winner_ids"]}})))
        }
        confirmed_ideas = [confirmed_map[idea_id] for idea_id in selected_category["winner_ids"] if idea_id in confirmed_map]
    return render_template(
        "core/dashboard.html",
        cycle=cycle,
        cycles=list(collection("cycles").find().sort("start_at", -1)),
        categories=categories,
        category_counts=category_counts,
        selected_category_id=selected_category_id,
        ideas=ideas_with_scores(ideas),
        selected_category=selected_category,
        confirmed_ideas=confirmed_ideas,
        total=total,
        cycle_total=cycle_total,
        page=page,
        per_page=current_app.config["PER_PAGE"],
    )


@core_bp.get("/final-winners")
@require_screen("core")
def final_winners():
    cycle = selected_cycle()
    categories = categories_for_cycle(cycle["_id"], active_only=False) if cycle else []
    grouped_winners = []
    if cycle:
        for category in categories:
            winner_ids = category.get("winner_ids", [])
            winners = []
            if winner_ids:
                winner_map = {
                    idea["idea_id"]: idea
                    for idea in ideas_with_scores(
                        list(collection("ideas").find({"idea_id": {"$in": winner_ids}, "archived": {"$ne": True}})),
                        str(category["_id"]),
                    )
                }
                winners = [winner_map[idea_id] for idea_id in winner_ids if idea_id in winner_map]
                winners = sorted(winners, key=lambda item: item.get("average_score", 0), reverse=True)
            grouped_winners.append({"category": category, "ideas": winners})
    return render_template(
        "core/final_winners.html",
        cycle=cycle,
        cycles=list(collection("cycles").find().sort("start_at", -1)),
        grouped_winners=grouped_winners,
    )


@core_bp.route("/cycles", methods=["GET", "POST"])
@require_screen("core")
def cycles():
    if request.method == "POST":
        name = grit_cycle_name(request.form.get("cycle_number"), request.form.get("year"))
        start_at = parse_datetime(request.form.get("start_at"))
        end_at = parse_datetime(request.form.get("end_at"))
        if not name or not start_at or not end_at or end_at <= start_at:
            flash("Cycle slot, year, start time, and a later stop time are required.", "error")
        elif collection("cycles").count_documents({"name": {"$regex": f"^GRIT-Cycle[12]-{name[-4:]}$"}}) >= 2:
            flash("Only two GRIT cycles are allowed for the selected year.", "error")
        else:
            create_cycle(name, start_at, end_at)
            flash("Cycle created with the default categories.", "success")
            return redirect(url_for("core.cycles"))
    return render_template("core/cycles.html", cycles=list(collection("cycles").find().sort("start_at", -1)))


@core_bp.post("/cycles/<cycle_id>/window")
@require_screen("core")
def update_cycle_window(cycle_id):
    start_at = parse_datetime(request.form.get("start_at"))
    end_at = parse_datetime(request.form.get("end_at"))
    if not start_at or not end_at or end_at <= start_at:
        flash("The cycle window was not changed. Choose a valid start and stop time.", "error")
    else:
        collection("cycles").update_one(
            {"_id": ObjectId(cycle_id)},
            {"$set": {"start_at": start_at, "end_at": end_at, "updated_at": utcnow()}},
        )
        flash("Submission window updated.", "success")
    return redirect(url_for("core.cycles"))


@core_bp.post("/cycles/<cycle_id>/release-jury")
@require_screen("core")
def release_jury(cycle_id):
    collection("cycles").update_one({"_id": ObjectId(cycle_id)}, {"$set": {"jury_released_at": utcnow(), "jury_closed_at": None}})
    flash("Ideas are released to assigned jury panels.", "success")
    return redirect(url_for("core.dashboard", cycle_id=cycle_id))


@core_bp.post("/cycles/<cycle_id>/withdraw-jury")
@require_screen("core")
def withdraw_jury(cycle_id):
    collection("cycles").update_one(
        {"_id": ObjectId(cycle_id)},
        {"$set": {"jury_released_at": None, "jury_closed_at": None, "updated_at": utcnow()}},
    )
    flash("Jury release withdrawn. Assigned jury panels cannot score until release is enabled again.", "success")
    return redirect(url_for("core.dashboard", cycle_id=cycle_id))


@core_bp.post("/cycles/<cycle_id>/close-jury")
@require_screen("core")
def close_jury(cycle_id):
    collection("cycles").update_one({"_id": ObjectId(cycle_id)}, {"$set": {"jury_closed_at": utcnow()}})
    flash("Jury visibility is closed for this cycle.", "success")
    return redirect(url_for("core.dashboard", cycle_id=cycle_id))


@core_bp.post("/cycles/<cycle_id>/archive")
@require_screen("core")
def archive_cycle(cycle_id):
    collection("cycles").update_one({"_id": ObjectId(cycle_id)}, {"$set": {"archived": True, "archived_at": utcnow()}})
    collection("ideas").update_many({"cycle_id": cycle_id}, {"$set": {"archived": True, "archived_at": utcnow()}})
    flash("Cycle archived. Entries moved to the archive view.", "success")
    return redirect(url_for("core.archive"))


@core_bp.get("/archive")
@require_screen("core")
def archive():
    cycles = list(collection("cycles").find({"archived": True}).sort("start_at", -1))
    cycle_id = request.args.get("cycle_id") or (str(cycles[0]["_id"]) if cycles else None)
    page = int(request.args.get("page", 1))
    query = {"archived": True}
    if cycle_id:
        query["cycle_id"] = cycle_id
    total = collection("ideas").count_documents(query)
    ideas = list(paged(collection("ideas").find(query).sort("created_at", -1), page, current_app.config["PER_PAGE"]))
    return render_template("core/archive.html", cycles=cycles, cycle_id=cycle_id, ideas=ideas, page=page, total=total, per_page=current_app.config["PER_PAGE"])


@core_bp.route("/users", methods=["GET", "POST"])
@require_screen("core")
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        if not username or not name or len(password) < 8 or role not in {"core", "jury", "jury_lead"}:
            flash("Add a username, name, role, and password of at least eight characters.", "error")
        else:
            create_user(username, name, password, role)
            flash("Portal account added.", "success")
            return redirect(url_for("core.users"))
    reset_requests = list(collection("password_reset_requests").find({"status": "open"}).sort("created_at", -1))
    return render_template("core/users.html", users=list(collection("users").find({"active": True}).sort("name", 1)), reset_requests=reset_requests)


@core_bp.post("/password-requests/<request_id>/resolve")
@require_screen("core")
def resolve_password_request(request_id):
    collection("password_reset_requests").update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "resolved", "resolved_at": utcnow(), "updated_at": utcnow()}},
    )
    flash("Password reset request marked resolved.", "success")
    return redirect(url_for("core.users"))


@core_bp.post("/categories/<category_id>/panel/users")
@require_screen("core")
def create_panel_user(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    if not category:
        abort(404, "Category not found.")
    username = request.form.get("username", "").strip().lower()
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "")
    if not username or not name or len(password) < 8 or role not in {"jury", "jury_lead"}:
        flash("Add jury name, username, role, and a password of at least eight characters.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    existing = collection("users").find_one({"username": username})
    user = existing or create_user(username, name, password, role)
    if existing:
        collection("users").update_one({"_id": existing["_id"]}, {"$set": {"name": name, "role": role, "active": True, "updated_at": utcnow()}})
        user = collection("users").find_one({"_id": existing["_id"]})
    field = "jury_lead_ids" if role == "jury_lead" else "jury_member_ids"
    current_ids = set(category.get(field, []))
    if field == "jury_lead_ids" and str(user["_id"]) not in current_ids and len(current_ids) >= 1:
        flash("Each category can have only one jury lead. Remove the current lead before adding another.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    if field == "jury_member_ids" and str(user["_id"]) not in current_ids and len(current_ids) >= 5:
        flash("Each category can have a maximum of five jury members.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    current_ids.add(str(user["_id"]))
    collection("categories").update_one(
        {"_id": category["_id"]},
        {"$set": {field: sorted(current_ids), "updated_at": utcnow()}},
    )
    flash("Jury account created and assigned to the category.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/users/<user_id>/delete")
@require_screen("core")
def delete_user(user_id):
    collection("users").update_one({"_id": ObjectId(user_id)}, {"$set": {"active": False, "disabled_at": utcnow()}})
    collection("categories").update_many(
        {},
        {"$pull": {"jury_member_ids": user_id, "jury_lead_ids": user_id}, "$set": {"updated_at": utcnow()}},
    )
    flash("Portal account disabled.", "success")
    next_url = request.form.get("next") or request.args.get("next")
    if next_url == "categories":
        cycle = selected_cycle()
        return redirect(url_for("core.categories", cycle_id=str(cycle["_id"]) if cycle else None))
    return redirect(url_for("core.users"))


@core_bp.post("/users/<user_id>/edit")
@require_screen("core")
def edit_user(user_id):
    role = request.form.get("role", "")
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")
    if not name or role not in {"core", "jury", "jury_lead"}:
        flash("Name and a valid role are required.", "error")
    elif password and len(password) < 8:
        flash("New password must be at least eight characters.", "error")
    else:
        payload = {"name": name, "role": role, "updated_at": utcnow()}
        if password:
            payload["password_hash"] = generate_password_hash(password)
        collection("users").update_one({"_id": ObjectId(user_id)}, {"$set": payload})
        flash("Portal account updated.", "success")
    return redirect(url_for("core.users"))


@core_bp.route("/categories", methods=["GET", "POST"])
@require_screen("core")
def categories():
    cycle = selected_cycle()
    if request.method == "POST":
        if not cycle:
            abort(404, "Create a cycle before adding categories.")
        if not request.form.get("name", "").strip():
            flash("Category name is required.", "error")
        else:
            upsert_category(cycle["_id"], request.form["name"], request.form.get("top_ideas_required", 10))
            flash("Category saved.", "success")
            return redirect(url_for("core.categories", cycle_id=str(cycle["_id"])))
    category_rows = categories_for_cycle(cycle["_id"], active_only=False) if cycle else []
    panel_warnings = []
    for category in category_rows:
        lead_count = len(category.get("jury_lead_ids", []))
        member_count = len(category.get("jury_member_ids", []))
        if lead_count != 1 or member_count < 3 or member_count > 5:
            details = []
            if lead_count == 0:
                details.append("missing jury lead")
            elif lead_count > 1:
                details.append(f"{lead_count} jury leads assigned; keep exactly 1")
            if member_count < 3:
                details.append(f"only {member_count} jury member(s); add at least {3 - member_count}")
            elif member_count > 5:
                details.append(f"{member_count} jury members assigned; remove {member_count - 5}")
            panel_warnings.append({"category": category["name"], "details": "; ".join(details)})
    jury_users = list(collection("users").find({"active": True, "role": {"$in": ["jury", "jury_lead"]}}).sort("name", 1))
    core_users = list(collection("users").find({"active": True, "role": "core"}).sort("name", 1))
    jury_user_map = {str(user["_id"]): user for user in jury_users}
    return render_template(
        "core/categories.html",
        cycle=cycle,
        cycles=list(collection("cycles").find().sort("start_at", -1)),
        categories=category_rows,
        jury_users=jury_users,
        core_users=core_users,
        jury_user_map=jury_user_map,
        panel_warnings=panel_warnings,
    )


@core_bp.post("/categories/core-users")
@require_screen("core")
def create_core_user_from_categories():
    cycle = selected_cycle()
    username = request.form.get("username", "").strip()
    name = request.form.get("name", "").strip()
    password = request.form.get("password", "")
    if not username or not name or len(password) < 8:
        flash("Add core member name, username, and password of at least eight characters.", "error")
    else:
        existing = collection("users").find_one({"username": username.lower()})
        if existing:
            collection("users").update_one(
                {"_id": existing["_id"]},
                {"$set": {"name": name, "role": "core", "active": True, "updated_at": utcnow()}},
            )
            if password:
                collection("users").update_one({"_id": existing["_id"]}, {"$set": {"password_hash": generate_password_hash(password)}})
            flash("Existing account restored as a core member.", "success")
        else:
            create_user(username, name, password, "core")
            flash("Core member account added.", "success")
    return redirect(url_for("core.categories", cycle_id=str(cycle["_id"]) if cycle else None))


@core_bp.post("/categories/<category_id>/edit")
@require_screen("core")
def edit_category(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    if not category:
        abort(404, "Category not found.")
    upsert_category(category["cycle_id"], request.form.get("name", category["name"]), request.form.get("top_ideas_required", category["top_ideas_required"]), category_id)
    flash("Category settings updated.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/categories/<category_id>/panel")
@require_screen("core")
def save_panel(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    member_ids = request.form.getlist("jury_member_ids")
    lead_ids = request.form.getlist("jury_lead_ids")
    if len(lead_ids) != 1:
        flash("Select exactly one jury lead for the category.", "error")
    elif not 3 <= len(member_ids) <= 5:
        flash("Select three to five jury members for the category.", "error")
    else:
        collection("categories").update_one(
            {"_id": ObjectId(category_id)},
            {"$set": {"jury_member_ids": member_ids, "jury_lead_ids": lead_ids, "updated_at": utcnow()}},
        )
        flash("Jury panel updated.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/categories/<category_id>/panel/add")
@require_screen("core")
def add_panel_user(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    user_id = request.form.get("user_id", "")
    panel_role = request.form.get("panel_role", "")
    field = "jury_lead_ids" if panel_role == "lead" else "jury_member_ids" if panel_role == "member" else ""
    user = collection("users").find_one({"_id": ObjectId(user_id), "active": True}) if user_id else None
    if not category or not user or not field:
        abort(400, "Valid category, user, and panel role are required.")
    if field == "jury_lead_ids" and user.get("role") != "jury_lead":
        flash("Select a jury lead account for the lead slot.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    if field == "jury_member_ids" and user.get("role") != "jury":
        flash("Select a jury member account for the member slot.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    ids = set(category.get(field, []))
    if field == "jury_lead_ids" and str(user["_id"]) not in ids and len(ids) >= 1:
        flash("Each category can have only one jury lead. Remove the current lead before adding another.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    if field == "jury_member_ids" and str(user["_id"]) not in ids and len(ids) >= 5:
        flash("Each category can have a maximum of five jury members.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    ids.add(str(user["_id"]))
    collection("categories").update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {field: sorted(ids), "updated_at": utcnow()}},
    )
    flash("Panel assignment added.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/categories/<category_id>/passwords")
@require_screen("core")
def reset_category_passwords(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    if not category:
        abort(404, "Category not found.")
    lead_password = request.form.get("jury_lead_password", "")
    member_password = request.form.get("jury_member_password", "")
    if not lead_password and not member_password:
        flash("Enter a jury lead password or a jury member password to update.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    if lead_password and len(lead_password) < 8:
        flash("Jury lead password must be at least eight characters.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    if member_password and len(member_password) < 8:
        flash("Jury member password must be at least eight characters.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))

    changed_user_ids = []
    if lead_password:
        for user_id in category.get("jury_lead_ids", []):
            collection("users").update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"password_hash": generate_password_hash(lead_password), "password_updated_at": utcnow(), "updated_at": utcnow()}},
            )
            changed_user_ids.append(user_id)
    if member_password:
        for user_id in category.get("jury_member_ids", []):
            collection("users").update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"password_hash": generate_password_hash(member_password), "password_updated_at": utcnow(), "updated_at": utcnow()}},
            )
            changed_user_ids.append(user_id)

    if changed_user_ids:
        collection("password_reset_requests").update_many(
            {"user_id": {"$in": changed_user_ids}, "status": "open"},
            {"$set": {"status": "resolved", "resolved_at": utcnow(), "updated_at": utcnow()}},
        )
    flash(f"Updated passwords for {len(changed_user_ids)} assigned jury account(s). Passwords are stored as hashes only.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/categories/<category_id>/panel/remove")
@require_screen("core")
def remove_panel_user(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    user_id = request.form.get("user_id", "")
    panel_role = request.form.get("panel_role", "")
    field = "jury_lead_ids" if panel_role == "lead" else "jury_member_ids" if panel_role == "member" else ""
    if category and user_id and (not field or user_id not in category.get(field, [])):
        if user_id in category.get("jury_member_ids", []):
            field = "jury_member_ids"
        elif user_id in category.get("jury_lead_ids", []):
            field = "jury_lead_ids"
    if not category or not user_id or not field:
        abort(400, "Valid category, user, and panel role are required.")
    collection("categories").update_one(
        {"_id": ObjectId(category_id)},
        {"$pull": {field: user_id}, "$set": {"updated_at": utcnow()}},
    )
    flash("Panel assignment removed. Add a replacement below if needed.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/categories/<category_id>/panel/remove-selected")
@require_screen("core")
def remove_selected_panel_users(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    if not category:
        abort(404, "Category not found.")
    lead_ids = set(request.form.getlist("jury_lead_remove_ids"))
    member_ids = set(request.form.getlist("jury_member_remove_ids"))
    if not lead_ids and not member_ids:
        flash("Select at least one assigned jury lead or member to remove.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    updated_leads = [user_id for user_id in category.get("jury_lead_ids", []) if user_id not in lead_ids]
    updated_members = [user_id for user_id in category.get("jury_member_ids", []) if user_id not in member_ids]
    collection("categories").update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"jury_lead_ids": updated_leads, "jury_member_ids": updated_members, "updated_at": utcnow()}},
    )
    removed_count = (len(category.get("jury_lead_ids", [])) - len(updated_leads)) + (len(category.get("jury_member_ids", [])) - len(updated_members))
    flash(f"{removed_count} jury assignment(s) removed from {category['name']}.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/categories/<category_id>/panel/remove-checked")
@require_screen("core")
def remove_checked_panel_users(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    if not category:
        abort(404, "Category not found.")
    checked_leads = set(request.form.getlist("jury_lead_ids"))
    checked_members = set(request.form.getlist("jury_member_ids"))
    selected_ids = checked_leads | checked_members
    assigned_leads = set(category.get("jury_lead_ids", []))
    assigned_members = set(category.get("jury_member_ids", []))
    lead_remove_ids = selected_ids & assigned_leads
    member_remove_ids = selected_ids & assigned_members
    if not lead_remove_ids and not member_remove_ids:
        flash("Select an assigned jury lead/member checkbox before clicking Remove selected.", "error")
        return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
    updated_leads = [user_id for user_id in category.get("jury_lead_ids", []) if user_id not in lead_remove_ids]
    updated_members = [user_id for user_id in category.get("jury_member_ids", []) if user_id not in member_remove_ids]
    collection("categories").update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"jury_lead_ids": updated_leads, "jury_member_ids": updated_members, "updated_at": utcnow()}},
    )
    removed_count = len(lead_remove_ids) + len(member_remove_ids)
    flash(f"{removed_count} jury assignment(s) removed from {category['name']}.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))


@core_bp.post("/categories/<category_id>/delete")
@require_screen("core")
def delete_category(category_id):
    category = collection("categories").find_one({"_id": ObjectId(category_id)})
    collection("categories").update_one({"_id": ObjectId(category_id)}, {"$set": {"active": False, "deleted_at": utcnow()}})
    flash("Category removed from new submissions. Existing ideas keep their history.", "success")
    return redirect(url_for("core.categories", cycle_id=category["cycle_id"]))
