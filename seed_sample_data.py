from datetime import timedelta

from app import create_app
from app.db import collection
from app.services import categories_for_cycle, create_cycle, upsert_seed_user
from app.utils import utcnow


SAMPLE_PASSWORD = "GirtDemo123!"
SAMPLE_ATTACHMENTS = [
    {"original_name": "sample-automation.png", "display_name": "Automation workflow preview", "path": "uploads/sample-automation.png"},
    {"original_name": "sample-process.png", "display_name": "Process improvement snapshot", "path": "uploads/sample-process.png"},
    {"original_name": "sample-architecture.png", "display_name": "Data architecture concept", "path": "uploads/sample-architecture.png"},
]
PROBLEMS = [
    "Reduce manual triage for production incidents.",
    "Shorten approval time for reusable solution submissions.",
    "Expose technical debt hotspots to delivery managers.",
    "Automate evidence collection for release governance.",
    "Reuse validated data transformations across project teams.",
    "Improve office workflow visibility for innovation sponsors.",
]
CATEGORY_PEOPLE = {
    "Unique Idea": ("Ananya Rao", ["Karan Malhotra", "Priya Menon", "Sahil Mathur", "Ira Mukherjee"]),
    "Solution Re-use": ("Rahul Iyer", ["Meera Subramanian", "Nikhil Bansal", "Tanvi Shah", "Harish Kumar"]),
    "Process Improvement": ("Sanjana Kapoor", ["Arjun Nair", "Neha Kulkarni", "Raghav Sinha", "Sneha Patil"]),
    "DevOps": ("Vikram Desai", ["Pooja Reddy", "Siddharth Jain", "Aman Verma", "Lakshmi Prasad"]),
    "Data Architecture": ("Aditi Sharma", ["Rohan Mehta", "Farah Khan", "Gaurav Mishra", "Nandini Rao"]),
    "Automation": ("Kavita Krishnan", ["Sameer Gupta", "Ishita Bose", "Pranav Rao", "Maya Nambiar"]),
    "Technical Debt": ("Ritesh Agarwal", ["Divya Narayanan", "Manav Chandra", "Shreya Ghosh", "Abhishek Tiwari"]),
}
CORE_MEMBERS = [
    ("core.demo", "Soma Chakraborty"),
    ("core.member2", "Amitabh Sen"),
    ("core.member3", "Renu Bhatia"),
    ("core.member4", "Prakash Nair"),
    ("core.member5", "Manisha Joshi"),
    ("core.member6", "Suresh Menon"),
    ("core.member7", "Devika Pillai"),
    ("core.member8", "Rohit Sethi"),
    ("core.member9", "Anita Rao"),
    ("core.member10", "Vivek Srinivasan"),
]
OWNER_NAMES = [
    ("Asha Raman", "asha.raman", "Meera Nair", "Bangalore", "India"),
    ("Vikram Singh", "vikram.singh", "Suresh Menon", "Mumbai", "India"),
    ("Neha Kulkarni", "neha.kulkarni", "Anita Rao", "Mumbai", "India"),
    ("Rahul Iyer", "rahul.iyer", "Prakash Nair", "Bangalore", "India"),
    ("Priya Menon", "priya.menon", "Devika Pillai", "Bangalore", "India"),
    ("Arjun Nair", "arjun.nair", "Rohit Sethi", "Mumbai", "India"),
    ("Sanjana Kapoor", "sanjana.kapoor", "Manisha Joshi", "Bangalore", "India"),
]
CATEGORY_JURY_PASSWORDS = {
    "Unique Idea": ("UniqueLead123!", "UniqueJury123!"),
    "Solution Re-use": ("ReuseLead123!", "ReuseJury123!"),
    "Process Improvement": ("ProcessLead123!", "ProcessJury123!"),
    "DevOps": ("DevOpsLead123!", "DevOpsJury123!"),
    "Data Architecture": ("DataLead123!", "DataJury123!"),
    "Automation": ("AutoLead123!", "AutoJury123!"),
    "Technical Debt": ("DebtLead123!", "DebtJury123!"),
}
SOLUTIONS = [
    "Route high-severity work through reusable automation and report the avoided queue time.",
    "Expose a reusable approval checklist so sponsors can see risk, owner, and rollout state together.",
    "Collect delivery signals into a governed data lane and highlight the decisions that need attention.",
    "Replace manual evidence chasing with event-driven capture and review-ready summaries.",
    "Standardize reusable transformation logic and make data quality checks visible before release.",
    "Use an innovation intake board that keeps contributors, sponsor, value case, and readiness aligned.",
]
HTML_DETAILS = [
    "<h2>Approach</h2><p>Instrument intake, automate routing, and publish decision metrics.</p><ul><li>Reusable workflow</li><li>Cycle-time measurement</li><li>Owner alerts</li></ul>",
    "<h2>Value</h2><p>Reduce repeat review effort with a shared approval pattern.</p><table><tr><th>Signal</th><th>Use</th></tr><tr><td>Risk</td><td>Prioritize review</td></tr></table>",
    "<h2>Architecture</h2><p>Collect data once, validate it, and expose ranked insights for managers.</p><blockquote>Designed for reuse across teams.</blockquote>",
]
PLAIN_DETAILS = [
    "Pilot plan:\n1. Select one delivery team.\n2. Baseline current manual time.\n3. Automate the routing step.\n4. Review sponsor feedback after two weeks.",
    "Controls:\n- FTE ownership captured\n- Sponsor confirmation required\n- Metrics retained for category review\n- Rollout can be staged by office location",
    "Expected outcome:\nFaster idea review, fewer repeat requests, clearer accountability, and a reusable dashboard for operations.",
]
PUBLIC_FEEDBACK = [
    ("Nisha Verma", "nisha.verma", "This can save real effort if the rollout metrics are visible.", "like"),
    ("Ajay Pillai", "ajay.pillai", "Good idea. Please add expected support ownership before scaling.", "neutral"),
    ("Bhavna Suri", "bhavna.suri", "Strong reuse possibility across delivery teams.", "like"),
]


def ensure_demo_cycle():
    legacy = collection("cycles").find_one({"name": "GIRT Cycle Demo,2026"})
    if legacy:
        collection("cycles").update_one({"_id": legacy["_id"]}, {"$set": {"archived": True, "archived_at": utcnow()}})
        collection("ideas").update_many({"cycle_id": str(legacy["_id"])}, {"$set": {"archived": True, "archived_at": utcnow()}})
    cycle = collection("cycles").find_one({"name": "GRIT-Cycle1-2026"})
    if cycle:
        collection("cycles").update_one(
            {"_id": cycle["_id"]},
            {"$set": {"start_at": utcnow() - timedelta(days=2), "end_at": utcnow() + timedelta(days=21), "archived": False}},
        )
        return collection("cycles").find_one({"_id": cycle["_id"]})
    cycle = create_cycle("GRIT-Cycle1-2026", utcnow() - timedelta(days=2), utcnow() + timedelta(days=21))
    return collection("cycles").find_one({"_id": cycle["_id"]})


def ensure_demo_idea(cycle, category_ids, suffix, problem, readiness, employee_id, attachment_index=0):
    idea_id = f"{cycle['name']}-{suffix}"
    legacy_id = f"{cycle['name']}-DEMO-{suffix}"
    existing = collection("ideas").find_one({"idea_id": idea_id}) or collection("ideas").find_one({"idea_id": legacy_id})
    owner_name, owner_username, sponsor, office_location, india_region = OWNER_NAMES[attachment_index % len(OWNER_NAMES)]
    co_owner = OWNER_NAMES[(attachment_index + 2) % len(OWNER_NAMES)]
    document = {
        "idea_id": idea_id,
        "edit_token": f"demo-edit-{suffix.lower()}",
        "cycle_id": str(cycle["_id"]),
        "problem_statement": problem,
        "solution_summary": SOLUTIONS[attachment_index % len(SOLUTIONS)],
        "video_link": "https://example.com/girt-demo-video",
        "can_be_patented": suffix == "001",
        "is_patented": False,
        "production_readiness": readiness,
        "contributors": [
            {"name": owner_name, "username": owner_username},
            {"name": co_owner[0], "username": co_owner[1]},
        ],
        "team_name": "GRIT Scale Team" if attachment_index % 9 == 0 else "",
        "officer_sponsor": sponsor,
        "content_format": "html" if attachment_index % 2 == 0 else "plain",
        "content": HTML_DETAILS[attachment_index % len(HTML_DETAILS)] if attachment_index % 2 == 0 else PLAIN_DETAILS[attachment_index % len(PLAIN_DETAILS)],
        "category_ids": category_ids,
        "owner_name": owner_name,
        "owner_employee_id": employee_id,
        "office_location": office_location,
        "india_region": india_region,
        "attachments": [SAMPLE_ATTACHMENTS[attachment_index % len(SAMPLE_ATTACHMENTS)]],
        "reaction_counts": {
            "like": 2 + (attachment_index % 8),
            "neutral": attachment_index % 3,
            "dislike": 1 if attachment_index % 11 == 0 else 0,
        },
        "public_comments": [
            {
                "name": PUBLIC_FEEDBACK[attachment_index % len(PUBLIC_FEEDBACK)][0],
                "username": PUBLIC_FEEDBACK[attachment_index % len(PUBLIC_FEEDBACK)][1],
                "comment": PUBLIC_FEEDBACK[attachment_index % len(PUBLIC_FEEDBACK)][2],
                "sentiment": PUBLIC_FEEDBACK[attachment_index % len(PUBLIC_FEEDBACK)][3],
                "created_at": utcnow(),
            }
        ] if attachment_index % 5 == 0 else [],
        "archived": False,
        "updated_at": utcnow(),
    }
    if existing:
        if existing.get("idea_id") == legacy_id:
            collection("evaluations").update_many({"idea_id": legacy_id}, {"$set": {"idea_id": idea_id, "updated_at": utcnow()}})
            collection("idea_reactions").update_many({"idea_id": legacy_id}, {"$set": {"idea_id": idea_id, "updated_at": utcnow()}})
        collection("ideas").update_one({"_id": existing["_id"]}, {"$set": document})
        return collection("ideas").find_one({"_id": existing["_id"]})
    document["created_at"] = utcnow()
    collection("ideas").insert_one(document)
    return collection("ideas").find_one({"idea_id": idea_id})


def seed():
    cycle = ensure_demo_cycle()
    for username, name in CORE_MEMBERS:
        upsert_seed_user(username, name, SAMPLE_PASSWORD, "core")
    upsert_seed_user("diptanun", "Diptanu Nath", "buntyyyy", "jury_lead")
    categories = categories_for_cycle(cycle["_id"])
    automation = next(category for category in categories if category["name"] == "Automation")
    process = next(category for category in categories if category["name"] == "Process Improvement")
    for category in collection("categories").find({"active": True}):
        if category["name"] not in CATEGORY_PEOPLE:
            continue
        slug = category.get("slug", category["name"].lower().replace(" ", ".")).replace("-", ".")
        lead_password, member_password = CATEGORY_JURY_PASSWORDS[category["name"]]
        lead_name, member_names = CATEGORY_PEOPLE[category["name"]]
        lead = upsert_seed_user(f"jury.lead.{slug}", lead_name, lead_password, "jury_lead")
        members = [
            upsert_seed_user(f"jury.member{index}.{slug}", member_name, member_password, "jury")
            for index, member_name in enumerate(member_names, start=1)
        ]
        collection("categories").update_one(
            {"_id": category["_id"]},
            {"$set": {"jury_lead_ids": [str(lead["_id"])], "jury_member_ids": [str(member["_id"]) for member in members], "top_ideas_required": 2, "active": True, "updated_at": utcnow()}},
        )
    readiness_values = ["yes", "in_6_months", "no"]
    ideas = []
    for index in range(1, 61):
        primary = categories[(index - 1) % len(categories)]
        category_ids = [str(primary["_id"])]
        if index % 4 == 0:
            category_ids.append(str(categories[index % len(categories)]["_id"]))
        ideas.append(
            ensure_demo_idea(
                cycle,
                category_ids,
                f"{index:03d}",
                PROBLEMS[(index - 1) % len(PROBLEMS)],
                readiness_values[(index - 1) % len(readiness_values)],
                f"GRIT{1000 + index}",
                index - 1,
            )
        )
    for category in categories:
        winner_ids = category.get("winner_ids", [])
        if winner_ids:
            collection("categories").update_one(
                {"_id": category["_id"]},
                {"$set": {"winner_ids": [idea_id.replace("-DEMO-", "-") for idea_id in winner_ids], "updated_at": utcnow()}},
            )
    evaluations = [
        (ideas[0], collection("users").find_one({"username": "jury.lead.automation"}), automation, 9, "Strong reuse potential.", "like"),
        (ideas[0], collection("users").find_one({"username": "jury.member1.automation"}), automation, 8, "Clear operating benefit.", "like"),
        (ideas[1], collection("users").find_one({"username": "jury.lead.process.improvement"}), process, 8, "Well scoped workflow.", "neutral"),
        (ideas[1], collection("users").find_one({"username": "jury.member2.process.improvement"}), process, 7, "Needs rollout detail.", "neutral"),
        (ideas[2], collection("users").find_one({"username": "jury.member1.process.improvement"}), process, 6, "Useful dashboard proposal.", "neutral"),
    ]
    for idea, juror, category, score, comment, sentiment in evaluations:
        collection("evaluations").update_one(
            {"idea_id": idea["idea_id"], "juror_id": str(juror["_id"])},
            {"$set": {"category_id": str(category["_id"]), "score": score, "comment": comment, "sentiment": sentiment, "juror_name": juror["name"], "updated_at": utcnow()}, "$setOnInsert": {"created_at": utcnow()}},
            upsert=True,
        )
    collection("ideas").update_one(
        {"idea_id": ideas[0]["idea_id"]},
        {"$set": {f"lead_comments.{str(automation['_id'])}": "Demo winner note for review handoff."}},
    )
    print("Sample GRIT data is ready.")
    print(f"Core login: core.demo / {SAMPLE_PASSWORD}")
    print("All-access test login: diptanun / buntyyyy")
    print("Automation lead: jury.lead.automation / AutoLead123!")
    print("Automation member: jury.member1.automation / AutoJury123!")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
