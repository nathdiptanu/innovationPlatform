# GRIT Login And First-Time Usage

GRIT is **Grassroot Innovation In Technology**.

## Local URLs

| Flow | URL | Login needed |
| --- | --- | --- |
| Public user portal | http://127.0.0.1:5000/users/ | No |
| Submit idea | http://127.0.0.1:5000/ideas/new | No |
| Portal login | http://127.0.0.1:5000/auth/login | Yes for core/jury |
| Core dashboard | http://127.0.0.1:5000/core/ | Core account |
| Core cycles | http://127.0.0.1:5000/core/cycles | Core account |
| Core categories and jury panels | http://127.0.0.1:5000/core/categories | Core account |
| Core final winners | http://127.0.0.1:5000/core/final-winners | Core account |
| Core accounts | http://127.0.0.1:5000/core/users | Core account |
| Jury portal | http://127.0.0.1:5000/jury/ | Assigned jury account |
| Swagger UI | http://127.0.0.1:5000/api/docs | Core account |
| OpenAPI JSON | http://127.0.0.1:5000/api/openapi.json | Core account |

## Core Committee Logins

All seeded core committee accounts use password `GirtDemo123!`.

This is only the seeded demo login password for core accounts. It is not used as a default idea edit access key; the idea submission access-key field is blank, and each submitter creates a private key for that idea.

| Name | Username | Password |
| --- | --- | --- |
| Soma Chakraborty | `core.demo` | `GirtDemo123!` |
| Amitabh Sen | `core.member2` | `GirtDemo123!` |
| Renu Bhatia | `core.member3` | `GirtDemo123!` |
| Prakash Nair | `core.member4` | `GirtDemo123!` |
| Manisha Joshi | `core.member5` | `GirtDemo123!` |
| Suresh Menon | `core.member6` | `GirtDemo123!` |
| Devika Pillai | `core.member7` | `GirtDemo123!` |
| Rohit Sethi | `core.member8` | `GirtDemo123!` |
| Anita Rao | `core.member9` | `GirtDemo123!` |
| Vivek Srinivasan | `core.member10` | `GirtDemo123!` |

Extra test account:

| Name | Username | Password | Notes |
| --- | --- | --- | --- |
| Diptanu Nath | `diptanun` | `buntyyyy` | Protected test login configured for core and jury screen access. Assign it to a category only if you want it to participate in jury review. |

## Jury Logins By Category

Each category has 1 jury lead and 4 jury members. Jury leads can see same-category averages, peer review counts, and same-category jury comments/scores. Jury members can score/comment and see only their own scored/pending state.

| Category | Role | Name | Username | Password |
| --- | --- | --- | --- | --- |
| Unique Idea | Lead | Ananya Rao | `jury.lead.unique.idea` | `UniqueLead123!` |
| Unique Idea | Member | Karan Malhotra | `jury.member1.unique.idea` | `UniqueJury123!` |
| Unique Idea | Member | Priya Menon | `jury.member2.unique.idea` | `UniqueJury123!` |
| Unique Idea | Member | Sahil Mathur | `jury.member3.unique.idea` | `UniqueJury123!` |
| Unique Idea | Member | Ira Mukherjee | `jury.member4.unique.idea` | `UniqueJury123!` |
| Solution Re-use | Lead | Rahul Iyer | `jury.lead.solution.re.use` | `ReuseLead123!` |
| Solution Re-use | Member | Meera Subramanian | `jury.member1.solution.re.use` | `ReuseJury123!` |
| Solution Re-use | Member | Nikhil Bansal | `jury.member2.solution.re.use` | `ReuseJury123!` |
| Solution Re-use | Member | Tanvi Shah | `jury.member3.solution.re.use` | `ReuseJury123!` |
| Solution Re-use | Member | Harish Kumar | `jury.member4.solution.re.use` | `ReuseJury123!` |
| Process Improvement | Lead | Sanjana Kapoor | `jury.lead.process.improvement` | `ProcessLead123!` |
| Process Improvement | Member | Arjun Nair | `jury.member1.process.improvement` | `ProcessJury123!` |
| Process Improvement | Member | Neha Kulkarni | `jury.member2.process.improvement` | `ProcessJury123!` |
| Process Improvement | Member | Raghav Sinha | `jury.member3.process.improvement` | `ProcessJury123!` |
| Process Improvement | Member | Sneha Patil | `jury.member4.process.improvement` | `ProcessJury123!` |
| DevOps | Lead | Vikram Desai | `jury.lead.devops` | `DevOpsLead123!` |
| DevOps | Member | Pooja Reddy | `jury.member1.devops` | `DevOpsJury123!` |
| DevOps | Member | Siddharth Jain | `jury.member2.devops` | `DevOpsJury123!` |
| DevOps | Member | Aman Verma | `jury.member3.devops` | `DevOpsJury123!` |
| DevOps | Member | Lakshmi Prasad | `jury.member4.devops` | `DevOpsJury123!` |
| Data Architecture | Lead | Aditi Sharma | `jury.lead.data.architecture` | `DataLead123!` |
| Data Architecture | Member | Rohan Mehta | `jury.member1.data.architecture` | `DataJury123!` |
| Data Architecture | Member | Farah Khan | `jury.member2.data.architecture` | `DataJury123!` |
| Data Architecture | Member | Gaurav Mishra | `jury.member3.data.architecture` | `DataJury123!` |
| Data Architecture | Member | Nandini Rao | `jury.member4.data.architecture` | `DataJury123!` |
| Automation | Lead | Kavita Krishnan | `jury.lead.automation` | `AutoLead123!` |
| Automation | Member | Sameer Gupta | `jury.member1.automation` | `AutoJury123!` |
| Automation | Member | Ishita Bose | `jury.member2.automation` | `AutoJury123!` |
| Automation | Member | Pranav Rao | `jury.member3.automation` | `AutoJury123!` |
| Automation | Member | Maya Nambiar | `jury.member4.automation` | `AutoJury123!` |
| Technical Debt | Lead | Ritesh Agarwal | `jury.lead.technical.debt` | `DebtLead123!` |
| Technical Debt | Member | Divya Narayanan | `jury.member1.technical.debt` | `DebtJury123!` |
| Technical Debt | Member | Manav Chandra | `jury.member2.technical.debt` | `DebtJury123!` |
| Technical Debt | Member | Shreya Ghosh | `jury.member3.technical.debt` | `DebtJury123!` |
| Technical Debt | Member | Abhishek Tiwari | `jury.member4.technical.debt` | `DebtJury123!` |

## First-Time Local Test Flow

1. Start the app:

   ```powershell
   python start_grit.py
   ```

   The demo currently uses SQLite because `config.ini` has `sqlite = yes`. Data is stored in `data/grit.sqlite3` and survives restarts.

2. Open http://127.0.0.1:5000/users/ and confirm the public idea gallery loads without login.
   Open an idea detail page to view images, image names, and public feedback. Any visitor can add an optional comment with like/neutral/dislike.

3. Log in at http://127.0.0.1:5000/auth/login using a core account, for example:

   `core.demo` / `GirtDemo123!`

4. Open http://127.0.0.1:5000/core/cycles and confirm the current GRIT cycle start and expiry date.
   This is the single deadline for all categories in that cycle.

5. Open http://127.0.0.1:5000/core/categories and review category panels.
   Each category should have exactly 1 jury lead and 3-5 jury members; the page shows a warning at the top when a panel is missing a lead or has too few/many members.
   Add jury access by checking the required lead/member and clicking **Save panel**.
   Remove jury access by clicking the red remove icon beside the assigned lead/member name and confirming twice.
   To add a new person directly from this page, use **Create and assign jury account**, enter name, username, temporary password, and role, then click **Add to panel**.
   To add an existing jury lead/member, use **Add existing jury lead** or **Add existing jury member**, select the available account, and click **Assign lead** or **Assign member**.
   Core committee members can also be added or disabled from the Core members panel on this same page.

6. Open http://127.0.0.1:5000/core/users to add, edit, disable, or change passwords for core/jury accounts.

7. Open http://127.0.0.1:5000/core/ and click **Release to jury** when the committee is ready.
   Jury scoring is blocked until this release step is done.
   For pre-production testing, click **Withdraw release** to pull the cycle back from jury and block scoring again.

8. Log out, then log in as a jury member or jury lead.
   Open http://127.0.0.1:5000/jury/.

9. Score ideas.
   Already-scored ideas are highlighted, pending ideas have a pending color, and the dashboard shows your scored/pending counts.

10. Log in as the category jury lead to see same-category averages, peer review counts, peer comments/scores, and the **Confirm top ideas** button.
    The category dashboard shows member scores/comments and the lead final comment column.
    Use **Refresh scores** after jury discussion if members update ratings.
    **Confirm top ideas** unlocks only after every assigned reviewer scores every idea, and asks for confirmation before finalizing.

11. Log back in as core and open http://127.0.0.1:5000/core/final-winners to see final winners grouped by category, sorted by score, with jury lead comments.

12. Close jury visibility or archive the cycle when the review is complete.

13. Use the core dashboard or archive filters to review patent candidates, already-patented ideas, and Mumbai/Bangalore location distribution.

## How Access Is Controlled

- Public user pages do not need login.
- Public users can search ideas from the gallery by idea ID, problem, solution, owner name, employee ID, or team name.
- All categories in a cycle share the same start and expiry date from `/core/cycles`.
- Public users can like/neutral/dislike an idea from the detail page. Counts are visible on both the gallery and detail page.
- Only the submitter with the submitter Employee ID plus private edit access key/session can edit an idea before jury release/archive.
- The edit token is generated at submission time for internal/API recovery and is visible only to core committee on the idea support page.
- Core committee can open an idea from the core dashboard/archive to view the saved internal edit token and reset the private edit access key when the submitter forgets it.
- After the due date, new submissions are blocked, but the submitter can still edit an existing idea until core releases the cycle to jury.
- After core releases the cycle to jury, idea edits and category changes are locked.
- Idea detail pages show submitted date and last edited date.
- Archived cycles are removed from active user, core, jury, and jury lead dashboards, and remain available from core archive.
- Core dashboard and archive pages include search, patent status, and office location filters for committee review.
- Core and jury login accounts live in MongoDB collection `users`.
- Passwords are stored as hashes, not plaintext.
- Jury leads and jury members can use `/auth/forgot-password`; core sees open reset requests on `/core/users`.
- Core can change an individual password on `/core/users`, or reset a category lead/member password set on `/core/categories`.
- For a category, all assigned jury members may share one password, while the assigned jury lead can have a different password. The app still stores only password hashes.
- Protected URL access is allowed in `app/access_config.py`.
- Category-level jury access is controlled in `/core/categories`.
- Jury lead/member add/remove is available in `/core/categories` with visible Add selected, Add to panel, and Remove controls.
- Core member add/disable is available in `/core/categories` and `/core/users`; the count of core members is not fixed.
- Jury score visibility is category-scoped. A lead/member from another category cannot see or score a different category unless core assigns that account to that category.
