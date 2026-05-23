import unittest
from datetime import datetime, timedelta, timezone

from app import create_app
from app.entitlements import can_access, is_assigned_to_category, is_idea_contributor
from app.utils import sanitize_content
from app.services import cycle_is_open, cycle_name_is_valid, grit_cycle_name, validate_idea


class ServiceUnitTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    def test_html_content_is_allow_list_cleaned(self):
        cleaned = sanitize_content(
            '<h2>Idea</h2><script>alert(1)</script><a href="javascript:bad()">Bad</a><p>Safe</p>',
            "html",
        )

        self.assertIn("<h2>Idea</h2>", cleaned)
        self.assertIn("<p>Safe</p>", cleaned)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("javascript:", cleaned)

    def test_idea_validation_requires_one_or_two_categories(self):
        payload = {
            "problem_statement": "Reduce manual effort.",
            "solution_summary": "Automate the workflow.",
            "production_readiness": "yes",
            "officer_sponsor": "Sponsor",
            "owner_name": "FTE Name",
            "owner_employee_id": "EMP001",
            "office_location": "Bengaluru",
            "india_region": "South India",
            "content": "Detailed solution",
            "contributors": [{"name": "FTE Name", "username": "fte.name"}],
            "category_ids": ["a", "b", "c"],
        }

        self.assertIn("Select one or two categories.", validate_idea(payload))

    def test_cycle_window_accepts_mongo_naive_datetimes(self):
        mongo_now = datetime.now(timezone.utc).replace(tzinfo=None)
        cycle = {
            "start_at": mongo_now - timedelta(hours=1),
            "end_at": mongo_now + timedelta(hours=1),
            "archived": False,
        }

        self.assertTrue(cycle_is_open(cycle))

    def test_core_username_is_not_granted_jury_screen(self):
        user = {"username": "core.demo", "role": "core"}

        self.assertTrue(can_access("core", user))
        self.assertFalse(can_access("jury", user))

    def test_jury_user_can_be_detected_as_idea_contributor(self):
        user = {"username": "jury.member.one"}
        idea = {"contributors": [{"username": "jury.member.one", "name": "Demo Juror"}]}

        self.assertTrue(is_idea_contributor(user, idea))

    def test_jury_category_assignment_funnels_member_and_lead_access(self):
        lead = {"_id": "lead-id", "username": "jury.lead.automation", "role": "jury_lead"}
        member = {"_id": "member-id", "username": "jury.member1.automation", "role": "jury"}
        category = {"jury_lead_ids": ["lead-id"], "jury_member_ids": ["member-id"]}

        self.assertTrue(is_assigned_to_category(lead, category))
        self.assertTrue(is_assigned_to_category(lead, category, lead_only=True))
        self.assertTrue(is_assigned_to_category(member, category))
        self.assertFalse(is_assigned_to_category(member, category, lead_only=True))

    def test_jury_account_cannot_review_unassigned_category(self):
        automation_member = {"_id": "automation-member", "username": "jury.member1.automation", "role": "jury"}
        process_category = {"jury_lead_ids": ["process-lead"], "jury_member_ids": ["process-member"]}

        self.assertFalse(is_assigned_to_category(automation_member, process_category))

    def test_cycle_names_use_two_grit_slots_per_year(self):
        self.assertTrue(cycle_name_is_valid("GRIT-Cycle1-2026"))
        self.assertTrue(cycle_name_is_valid("GRIT-Cycle2-2026"))
        self.assertFalse(cycle_name_is_valid("GRIT-Cycle3-2026"))
        self.assertEqual(grit_cycle_name(2, 2027), "GRIT-Cycle2-2027")


if __name__ == "__main__":
    unittest.main()
