def _response(description, schema=None):
    item = {"description": description}
    if schema:
        item["content"] = {"application/json": {"schema": schema}}
    return item


def _html_response(description="Rendered HTML page"):
    return {"description": description, "content": {"text/html": {"schema": {"type": "string"}}}}


def _redirect(description="Redirects after completing the form action"):
    return {"description": description}


def _form(properties, required=None):
    return {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "type": "object",
                    "required": required or [],
                    "properties": properties,
                }
            }
        },
    }


def _json(schema):
    return {"required": True, "content": {"application/json": {"schema": schema}}}


def _path_param(name, description):
    return {"name": name, "in": "path", "required": True, "description": description, "schema": {"type": "string"}}


def _query_param(name, description, schema=None, required=False):
    return {"name": name, "in": "query", "required": required, "description": description, "schema": schema or {"type": "string"}}


def _op(tag, summary, description, responses=None, parameters=None, request_body=None, security=None):
    operation = {
        "tags": [tag],
        "summary": summary,
        "description": description,
        "responses": responses or {"200": _html_response()},
    }
    if parameters:
        operation["parameters"] = parameters
    if request_body:
        operation["requestBody"] = request_body
    if security is not None:
        operation["security"] = security
    return operation


def build_openapi():
    cookie_security = [{"cookieAuth": []}]
    core_security = [{"cookieAuth": ["core"]}]
    jury_security = [{"cookieAuth": ["jury"]}]
    idea_id = _path_param("idea_id", "Unique GRIT idea ID, for example GRIT-Cycle1-2026-045.")
    category_id = _path_param("category_id", "Mongo ObjectId / SQLite-compatible ID of the category.")
    cycle_id = _path_param("cycle_id", "Mongo ObjectId / SQLite-compatible ID of the cycle.")
    user_id = _path_param("user_id", "Mongo ObjectId / SQLite-compatible ID of the portal user.")

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "GRIT Competition API",
            "version": "1.2.0",
            "description": (
                "Complete API and portal route contract for Grassroot Innovation In Technology. "
                "JSON endpoints are under /api. HTML form endpoints are also listed because they "
                "change cycle, category, jury, idea, and winner state."
            ),
        },
        "servers": [{"url": "/"}],
        "tags": [
            {"name": "Public", "description": "Public entrant browsing, submission, comments, reactions, and edit-token flows."},
            {"name": "Auth", "description": "Session login/logout for core and jury portals."},
            {"name": "API", "description": "JSON endpoints intended for integration or Swagger testing."},
            {"name": "Core", "description": "Core committee cycle, account, category, jury panel, release, archive, and winner-management actions."},
            {"name": "Jury", "description": "Category-scoped jury scoring and jury-lead winner confirmation actions."},
            {"name": "Docs", "description": "Core-protected Swagger UI and OpenAPI JSON."},
        ],
        "paths": {
            "/": {
                "get": _op("Public", "Landing redirect", "Routes visitors to the public user idea workspace.", {"302": _redirect("Redirects to /users/.")})
            },
            "/users/": {
                "get": _op(
                    "Public",
                    "Browse submitted ideas",
                    "Public idea gallery with category tabs, search, pagination, total idea count, and cycle countdown.",
                    {"200": _html_response()},
                    [_query_param("category_id", "Optional category filter."), _query_param("q", "Search idea ID, problem, solution, owner, employee ID, or team name."), _query_param("page", "Page number.", {"type": "integer", "minimum": 1})],
                )
            },
            "/ideas/new": {
                "get": _op("Public", "Render idea submission form", "Shows the entrant form when the active cycle allows submission.", {"200": _html_response(), "409": _html_response("Submission closed page")}),
                "post": _op(
                    "Public",
                    "Submit new idea with attachments",
                    "Creates a GRIT idea, stores contributors, optional HTML/plain detail content, image attachments, and returns a success page with edit token.",
                    {"200": _html_response("Submission receipt"), "400": _html_response("Validation errors"), "409": _html_response("Submission window closed")},
                    request_body=_form({"problem_statement": {"type": "string"}, "solution_summary": {"type": "string"}, "video_link": {"type": "string"}, "can_be_patented": {"type": "string"}, "is_patented": {"type": "string"}, "production_readiness": {"type": "string"}, "officer_sponsor": {"type": "string"}, "content_format": {"type": "string"}, "content": {"type": "string"}, "owner_name": {"type": "string"}, "owner_employee_id": {"type": "string"}, "edit_pin": {"type": "string", "format": "password", "minLength": 8}, "office_location": {"type": "string"}, "country": {"type": "string"}, "team_name": {"type": "string"}, "category_ids": {"type": "array", "items": {"type": "string"}}}),
                ),
            },
            "/ideas/{idea_id}": {
                "get": _op("Public", "View idea detail", "Shows full idea content, image previews, comments, like counts, and metadata.", {"200": _html_response(), "404": _html_response("Idea not found")}, [idea_id])
            },
            "/ideas/{idea_id}/comments": {
                "post": _op("Public", "Add public comment", "Stores an optional visitor comment against an idea for later viewing.", {"302": _redirect(), "404": _html_response("Idea not found")}, [idea_id], _form({"commenter_name": {"type": "string"}, "comment": {"type": "string"}}, ["comment"]))
            },
            "/ideas/{idea_id}/react": {
                "post": _op("Public", "Like/dislike/neutral reaction", "Stores a visitor reaction and updates visible reaction counts.", {"302": _redirect(), "404": _html_response("Idea not found")}, [idea_id], _form({"reaction": {"type": "string", "enum": ["like", "dislike", "neutral"]}}, ["reaction"]))
            },
            "/ideas/{idea_id}/edit": {
                "get": _op("Public", "Render edit idea form", "Shows the edit form when the submitter browser session is active. If the session expired, returns an unlock form that requires edit token plus private edit passcode.", {"200": _html_response(), "403": _html_response("Unlock form or invalid edit proof"), "409": _html_response("Editing locked")}, [idea_id, _query_param("token", "Edit token returned on submission.")]),
                "post": _op("Public", "Edit existing idea", "Updates idea fields before jury release locks editing. If the browser session expired, posting edit_token plus edit_pin restores the session before editing.", {"302": _redirect(), "400": _html_response("Validation errors"), "403": _html_response("Invalid edit proof"), "409": _html_response("Editing locked")}, [idea_id, _query_param("token", "Edit token returned on submission.")]),
            },
            "/auth/login": {
                "get": _op("Auth", "Render login page", "Shows protected portal login for core committee and jury users.", {"200": _html_response()}),
                "post": _op("Auth", "Create session", "Validates username/password from the users collection and starts a Flask session.", {"302": _redirect("Redirects to the user's allowed portal."), "200": _html_response("Login failed and page re-rendered")}, request_body=_form({"username": {"type": "string"}, "password": {"type": "string", "format": "password"}}, ["username", "password"])),
            },
            "/auth/forgot-password": {
                "get": _op("Auth", "Render forgot password page", "Shows the jury password reset request form.", {"200": _html_response()}),
                "post": _op("Auth", "Submit password reset request", "Records an open reset request for active jury/jury lead accounts without revealing whether the username exists.", {"302": _redirect("Redirects back to login with a generic success message.")}, request_body=_form({"username": {"type": "string"}}, ["username"])),
            },
            "/auth/logout": {
                "get": _op("Auth", "Clear session", "Logs out the current protected portal user.", {"302": _redirect("Redirects to public home.")}, security=cookie_security)
            },
            "/api/docs": {
                "get": _op("Docs", "Swagger UI", "Core-only Swagger UI for exploring the GRIT API and portal route contract.", {"200": _html_response(), "302": _redirect("Redirects to login when not authenticated."), "403": _html_response("Core access required")}, security=core_security)
            },
            "/api/openapi.json": {
                "get": _op("Docs", "OpenAPI JSON", "Core-only OpenAPI 3.0 JSON document used by Swagger UI.", {"200": _response("OpenAPI document", {"type": "object"}), "302": _redirect("Redirects to login when not authenticated."), "403": _html_response("Core access required")}, security=core_security)
            },
            "/api/cycles/current": {
                "get": _op("API", "Get current cycle", "Returns the active non-archived cycle and whether submissions are currently open.", {"200": _response("Current cycle or null", {"oneOf": [{"$ref": "#/components/schemas/Cycle"}, {"nullable": True}]})})
            },
            "/api/categories": {
                "get": _op("API", "List current cycle categories", "Returns active categories for the current cycle with winner targets.", {"200": _response("Category list", {"type": "array", "items": {"$ref": "#/components/schemas/Category"}})})
            },
            "/api/ideas": {
                "get": _op("API", "Search ideas", "Searches non-archived ideas by idea ID, problem statement, or employee ID with pagination.", {"200": _response("Paged ideas", {"$ref": "#/components/schemas/IdeaPage"})}, [_query_param("q", "Search text."), _query_param("page", "Page number.", {"type": "integer", "minimum": 1})]),
                "post": _op("API", "Submit idea as JSON", "Creates an idea via JSON while the submission window is open. Image upload remains on the web form.", {"201": _response("Idea created", {"$ref": "#/components/schemas/IdeaReceipt"}), "400": _response("Validation error"), "409": _response("Submission window closed")}, request_body=_json({"$ref": "#/components/schemas/IdeaInput"})),
            },
            "/api/ideas/{idea_id}": {
                "get": _op("API", "Get idea JSON", "Returns one non-archived idea without exposing the edit token.", {"200": _response("Idea", {"$ref": "#/components/schemas/Idea"}), "404": _response("Idea not found")}, [idea_id]),
                "put": _op("API", "Edit idea as JSON", "Updates an idea when the X-Edit-Token header is valid and the cycle is open.", {"200": _response("Updated idea", {"$ref": "#/components/schemas/Idea"}), "400": _response("Validation error"), "403": _response("Missing or invalid edit token"), "409": _response("Cycle closed"), "404": _response("Idea not found")}, [idea_id, {"$ref": "#/components/parameters/EditToken"}], _json({"$ref": "#/components/schemas/IdeaInput"})),
            },
            "/api/core/dashboard": {
                "get": _op("API", "Core dashboard counts JSON", "Returns current cycle category counts for core dashboards and management reporting.", {"200": _response("Dashboard counts", {"$ref": "#/components/schemas/CoreDashboard"}), "403": _response("Core access required")}, security=core_security)
            },
            "/core/": {
                "get": _op(
                    "Core",
                    "Core dashboard",
                    "Management dashboard with total submissions, per-category counts, countdown, release controls, cycle state, patent/location filters, and governance watchlist.",
                    {"200": _html_response(), "302": _redirect("Login required"), "403": _html_response("Core access required")},
                    [_query_param("cycle_id", "Optional cycle ID."), _query_param("category_id", "Optional category ID."), _query_param("q", "Search idea ID, problem, owner, employee ID, or team."), _query_param("patent", "Patent filter.", {"type": "string", "enum": ["", "can_be_patented", "is_patented", "not_marked"]}), _query_param("office_location", "Office location filter.", {"type": "string", "enum": ["", "Mumbai", "Bangalore"]}), _query_param("page", "Page number.", {"type": "integer", "minimum": 1})],
                    security=core_security,
                )
            },
            "/core/final-winners": {
                "get": _op("Core", "Final winners", "Shows jury-lead-confirmed winners grouped by category, sorted by score, with lead comments.", {"200": _html_response(), "403": _html_response("Core access required")}, security=core_security)
            },
            "/core/ideas/{idea_id}": {
                "get": _op("Core", "Core idea edit support", "Core-only page showing the saved edit token for an idea and whether editing is locked. The edit passcode remains hashed and is not viewable.", {"200": _html_response(), "404": _html_response("Idea not found")}, [idea_id], security=core_security)
            },
            "/core/ideas/{idea_id}/edit-access": {
                "post": _op("Core", "Reset idea edit passcode", "Core-only action that sets a new temporary edit passcode hash for a submitter who forgot their private passcode.", {"302": _redirect(), "404": _html_response("Idea not found")}, [idea_id], _form({"edit_pin": {"type": "string", "format": "password", "minLength": 8}}, ["edit_pin"]), core_security)
            },
            "/core/cycles": {
                "get": _op("Core", "Manage cycles", "Shows cycle setup, six-month naming, start/end window, and active cycle controls.", {"200": _html_response()}, security=core_security),
                "post": _op("Core", "Create cycle", "Creates a new GRIT cycle with shared start/end dates across all categories.", {"302": _redirect()}, request_body=_form({"cycle_number": {"type": "integer", "enum": [1, 2]}, "year": {"type": "integer"}, "start_at": {"type": "string"}, "end_at": {"type": "string"}}), security=core_security),
            },
            "/core/cycles/{cycle_id}/window": {
                "post": _op("Core", "Update cycle window", "Changes the single start and expiry date used by every category in the cycle.", {"302": _redirect()}, [cycle_id], _form({"start_at": {"type": "string"}, "end_at": {"type": "string"}}, ["start_at", "end_at"]), core_security)
            },
            "/core/cycles/{cycle_id}/release-jury": {
                "post": _op("Core", "Release cycle to jury", "Makes released ideas visible and scoreable to assigned jury leads/members.", {"302": _redirect()}, [cycle_id], security=core_security)
            },
            "/core/cycles/{cycle_id}/withdraw-jury": {
                "post": _op("Core", "Withdraw jury release", "Testing control that hides released ideas from jury and blocks scoring again.", {"302": _redirect()}, [cycle_id], security=core_security)
            },
            "/core/cycles/{cycle_id}/close-jury": {
                "post": _op("Core", "Close jury evaluation", "Removes ideas from active jury screens after evaluation is complete.", {"302": _redirect()}, [cycle_id], security=core_security)
            },
            "/core/cycles/{cycle_id}/archive": {
                "post": _op("Core", "Archive cycle", "Moves a cycle and its ideas out of active user, core, and jury dashboards while preserving archive history.", {"302": _redirect()}, [cycle_id], security=core_security)
            },
            "/core/archive": {
                "get": _op(
                    "Core",
                    "Archive view",
                    "Shows archived cycle ideas with search, patent status, and office location filters for historical review.",
                    {"200": _html_response()},
                    [_query_param("cycle_id", "Archived cycle ID."), _query_param("q", "Search idea ID, problem, owner, employee ID, or team."), _query_param("patent", "Patent filter.", {"type": "string", "enum": ["", "can_be_patented", "is_patented", "not_marked"]}), _query_param("office_location", "Office location filter.", {"type": "string", "enum": ["", "Mumbai", "Bangalore"]}), _query_param("page", "Page number.", {"type": "integer", "minimum": 1})],
                    security=core_security,
                )
            },
            "/core/users": {
                "get": _op("Core", "Manage portal accounts", "Shows active core, jury lead, and jury member accounts.", {"200": _html_response()}, security=core_security),
                "post": _op("Core", "Create portal account", "Creates a protected portal account with hashed password and role.", {"302": _redirect()}, request_body=_form({"username": {"type": "string"}, "name": {"type": "string"}, "password": {"type": "string", "format": "password"}, "role": {"type": "string", "enum": ["core", "jury", "jury_lead"]}}, ["username", "name", "password", "role"]), security=core_security),
            },
            "/core/users/{user_id}/edit": {
                "post": _op("Core", "Edit portal account", "Updates name, role, and optionally password for a protected portal account.", {"302": _redirect()}, [user_id], _form({"name": {"type": "string"}, "role": {"type": "string", "enum": ["core", "jury", "jury_lead"]}, "password": {"type": "string", "format": "password"}}), core_security)
            },
            "/core/users/{user_id}/delete": {
                "post": _op("Core", "Disable portal account", "Soft-disables an account and removes it from all category jury assignments.", {"302": _redirect()}, [user_id], _form({"next": {"type": "string"}}), core_security)
            },
            "/core/password-requests/{request_id}/resolve": {
                "post": _op("Core", "Resolve password reset request", "Marks a jury forgot-password request as resolved after core resets or handles the account password.", {"302": _redirect()}, [_path_param("request_id", "Password reset request ID.")], security=core_security)
            },
            "/core/categories": {
                "get": _op("Core", "Manage categories and panels", "Shows category settings, winner target, panel warnings, add/remove jury lead/member controls, and core committee shortcuts.", {"200": _html_response()}, [_query_param("cycle_id", "Optional cycle ID to manage.")], security=core_security),
                "post": _op("Core", "Create category", "Adds a category to the selected cycle with a winner target.", {"302": _redirect()}, request_body=_form({"name": {"type": "string"}, "top_ideas_required": {"type": "integer", "minimum": 1}}, ["name", "top_ideas_required"]), security=core_security),
            },
            "/core/categories/core-users": {
                "post": _op("Core", "Create core user from categories page", "Adds or restores a core committee account from the category management page.", {"302": _redirect()}, request_body=_form({"username": {"type": "string"}, "name": {"type": "string"}, "password": {"type": "string", "format": "password"}}, ["username", "name", "password"]), security=core_security)
            },
            "/core/categories/{category_id}/edit": {
                "post": _op("Core", "Edit category", "Renames a category and updates its winner target count.", {"302": _redirect()}, [category_id], _form({"name": {"type": "string"}, "top_ideas_required": {"type": "integer", "minimum": 1}}, ["name", "top_ideas_required"]), core_security)
            },
            "/core/categories/{category_id}/panel": {
                "post": _op("Core", "Bulk save jury panel", "Saves exactly one jury lead and three to five jury members for a category from checkbox selections.", {"302": _redirect()}, [category_id], _form({"jury_lead_ids": {"type": "array", "items": {"type": "string"}}, "jury_member_ids": {"type": "array", "items": {"type": "string"}}}), core_security)
            },
            "/core/categories/{category_id}/panel/add": {
                "post": _op("Core", "Assign existing jury account", "Adds an existing jury lead or jury member account to a category panel while enforcing one lead and at most five members.", {"302": _redirect()}, [category_id], _form({"user_id": {"type": "string"}, "panel_role": {"type": "string", "enum": ["lead", "member"]}}, ["user_id", "panel_role"]), core_security)
            },
            "/core/categories/{category_id}/passwords": {
                "post": _op("Core", "Reset category jury passwords", "Core-only action to reset the assigned lead password and/or all assigned jury member passwords for one category. Passwords are hashed before storage.", {"302": _redirect()}, [category_id], _form({"jury_lead_password": {"type": "string", "format": "password"}, "jury_member_password": {"type": "string", "format": "password"}}), core_security)
            },
            "/core/categories/{category_id}/panel/remove": {
                "post": _op("Core", "Remove jury assignment", "Removes one assigned jury lead or jury member from a category panel. The UI double-confirms this action.", {"302": _redirect()}, [category_id], _form({"user_id": {"type": "string"}, "panel_role": {"type": "string", "enum": ["lead", "member"]}}, ["user_id", "panel_role"]), core_security)
            },
            "/core/categories/{category_id}/panel/users": {
                "post": _op("Core", "Create and assign jury account", "Creates a new jury lead/member account with password and assigns it directly to the category panel.", {"302": _redirect()}, [category_id], _form({"name": {"type": "string"}, "username": {"type": "string"}, "password": {"type": "string", "format": "password"}, "role": {"type": "string", "enum": ["jury", "jury_lead"]}}, ["name", "username", "password", "role"]), core_security)
            },
            "/core/categories/{category_id}/panel/remove-selected": {
                "post": _op("Core", "Remove selected jury assignments", "Legacy bulk endpoint for removing checked lead/member IDs from a category panel.", {"302": _redirect()}, [category_id], _form({"jury_lead_remove_ids": {"type": "array", "items": {"type": "string"}}, "jury_member_remove_ids": {"type": "array", "items": {"type": "string"}}}), core_security)
            },
            "/core/categories/{category_id}/panel/remove-checked": {
                "post": _op("Core", "Remove checked jury assignments", "Compatibility endpoint that removes selected IDs from either the lead or member assignment list.", {"302": _redirect()}, [category_id], _form({"jury_lead_ids": {"type": "array", "items": {"type": "string"}}, "jury_member_ids": {"type": "array", "items": {"type": "string"}}}), core_security)
            },
            "/core/categories/{category_id}/delete": {
                "post": _op("Core", "Deactivate category", "Soft-removes a category from new submissions while preserving existing idea history.", {"302": _redirect()}, [category_id], security=core_security)
            },
            "/jury/": {
                "get": _op("Jury", "Jury dashboard", "Shows only released categories assigned to the logged-in jury lead/member, with score state and pending counts.", {"200": _html_response(), "403": _html_response("Jury access required")}, [_query_param("category_id", "Optional assigned category ID."), _query_param("page", "Page number.", {"type": "integer", "minimum": 1})], security=jury_security)
            },
            "/jury/ideas/{idea_id}": {
                "get": _op("Jury", "Review idea", "Shows an assigned idea for scoring and, for leads, peer scores/comments in that category.", {"200": _html_response(), "403": _html_response("Not assigned"), "404": _html_response("Idea not found")}, [idea_id, _query_param("category_id", "Category being evaluated.")], security=jury_security),
                "post": _op("Jury", "Submit jury score", "Stores a 1-10 score, juror comment, and sentiment signal for the idea/category/juror.", {"302": _redirect(), "403": _html_response("Not assigned"), "409": _html_response("Jury not released or closed")}, [idea_id], _form({"category_id": {"type": "string"}, "score": {"type": "integer", "minimum": 1, "maximum": 10}, "comments": {"type": "string"}, "sentiment": {"type": "string", "enum": ["like", "dislike", "neutral"]}}, ["category_id", "score"]), jury_security)
            },
            "/jury/ideas/{idea_id}/lead-comment": {
                "post": _op("Jury", "Save jury lead final comment", "Stores the assigned jury lead's final reference comment for an idea in the category.", {"302": _redirect(), "403": _html_response("Lead access required")}, [idea_id], _form({"category_id": {"type": "string"}, "lead_comment": {"type": "string"}}, ["category_id"]), jury_security)
            },
            "/jury/categories/{category_id}/confirm": {
                "post": _op("Jury", "Confirm top ideas", "Lead-only finalization of top ideas for a category after all assigned reviewers have scored every released idea.", {"302": _redirect(), "403": _html_response("Lead access required"), "409": _html_response("Scoring incomplete")}, [category_id], security=jury_security)
            },
        },
        "components": {
            "securitySchemes": {"cookieAuth": {"type": "apiKey", "in": "cookie", "name": "session", "description": "Flask session cookie created by /auth/login."}},
            "parameters": {"EditToken": {"name": "X-Edit-Token", "in": "header", "required": True, "description": "Edit token returned when an idea is submitted.", "schema": {"type": "string"}}},
            "schemas": {
                "Cycle": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "start_at": {"type": "string", "format": "date-time"}, "end_at": {"type": "string", "format": "date-time"}, "submission_open": {"type": "boolean"}}},
                "Category": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "top_ideas_required": {"type": "integer"}}},
                "Contributor": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "username": {"type": "string"}}},
                "IdeaInput": {
                    "type": "object",
                    "required": ["problem_statement", "solution_summary", "production_readiness", "contributors", "officer_sponsor", "content", "category_ids", "owner_name", "owner_employee_id", "office_location", "edit_pin"],
                    "properties": {
                        "problem_statement": {"type": "string", "description": "Problem being solved."},
                        "solution_summary": {"type": "string", "description": "Short proposed solution."},
                        "video_link": {"type": "string", "format": "uri"},
                        "can_be_patented": {"type": "boolean"},
                        "is_patented": {"type": "boolean"},
                        "production_readiness": {"type": "string", "enum": ["yes", "no", "in_6_months"], "description": "Whether other users can use it now, not yet, or within six months."},
                        "contributors": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"$ref": "#/components/schemas/Contributor"}},
                        "team_name": {"type": "string"},
                        "officer_sponsor": {"type": "string", "description": "VP and above sponsor."},
                        "content_format": {"type": "string", "enum": ["plain", "html"]},
                        "content": {"type": "string", "description": "Detailed idea content; HTML is sanitized by allow-list."},
                        "category_ids": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string"}},
                        "owner_name": {"type": "string"},
                        "owner_employee_id": {"type": "string"},
                        "edit_pin": {"type": "string", "format": "password", "minLength": 8, "description": "Private edit passcode for session recovery. Stored only as a hash."},
                        "office_location": {"type": "string", "enum": ["Mumbai", "Bangalore"]},
                        "country": {"type": "string", "default": "India"},
                    },
                },
                "Idea": {"allOf": [{"$ref": "#/components/schemas/IdeaInput"}, {"type": "object", "properties": {"idea_id": {"type": "string"}, "created_at": {"type": "string", "format": "date-time"}, "updated_at": {"type": "string", "format": "date-time"}}}]},
                "IdeaReceipt": {"type": "object", "properties": {"idea_id": {"type": "string"}, "edit_token": {"type": "string"}, "edit_url": {"type": "string"}}},
                "IdeaPage": {"type": "object", "properties": {"items": {"type": "array", "items": {"$ref": "#/components/schemas/Idea"}}, "page": {"type": "integer"}, "total": {"type": "integer"}}},
                "CoreDashboard": {"type": "object", "properties": {"cycle": {"type": "object", "nullable": True}, "counts": {"type": "array", "items": {"type": "object", "properties": {"category_id": {"type": "string"}, "name": {"type": "string"}, "ideas": {"type": "integer"}}}}}},
            },
        },
    }
