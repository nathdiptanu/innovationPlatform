# GRIT Code Guide

## Package map

| File | Purpose |
| --- | --- |
| `run.py` | Flask entrypoint |
| `start_grit.py` | One-command setup, sample seed, and Flask local start |
| `app/config.py` | Environment and UI defaults |
| `app/db.py` | Mongo client, collection names, indexes |
| `app/access_config.py` | Username-to-protected-screen access map |
| `app/entitlements.py` | Screen permission and category assignment rules |
| `app/services.py` | Cycle, category, idea, user, score helpers |
| `app/public.py` | Public idea submission/search/edit routes |
| `app/core.py` | Core committee routes |
| `app/jury.py` | Jury review routes |
| `app/api.py` | JSON API and Swagger/OpenAPI routes |
| `app/openapi.py` | OpenAPI 3 schema document |
| `app/templates/` | Server-rendered web UI |
| `app/static/` | Styling, preview behavior, upload target |
| `seed_sample_data.py` | Repeatable demo cycle, accounts, ideas, and evaluations |
| `tests/` | Unit and Flask route integration checks |

## Data flow

1. A core user creates a cycle in `app/core.py`.
2. `create_cycle()` stores the cycle and seeds default categories from `Config.DEFAULT_CATEGORIES`.
3. The public form uses `idea_payload()` and `validate_idea()` before insert/update.
4. HTML content is cleaned by the allow-list sanitizer in `sanitize_content()` before it reaches MongoDB.
5. BSON size is checked before MongoDB writes. Images are stored under `app/static/uploads` and MongoDB keeps attachment metadata.
6. Jury release is cycle state. A jury user only sees assigned categories when `cycle_accepts_jury()` is true.
7. Evaluations are unique per idea and juror. Score summaries are calculated from the `evaluations` collection.
8. Jury lead confirmation stores the currently ranked winner IDs on the category document.

## Entitlement changes

Change username-to-screen visibility in `USER_SCREEN_ACCESS` inside `app/access_config.py`. Keep category-specific jury policy in:

- `is_assigned_to_category()`
- `require_category_assignment()`

Core usernames should have `{"core"}` and jury usernames should have `{"jury"}`. The shipped config intentionally keeps the core portal out of jury URLs and jury accounts out of core URLs. That keeps future entitlement changes away from form and template logic.

## Typical extensions

- Add enterprise SSO by replacing the session login logic in `app/auth.py` while keeping `g.user`.
- Add audit logging by writing events to `audit_events` from core and jury mutations.
- Move attachments to object storage by changing `save_images()` and the image URL template.
- Add email or Teams notifications after jury release and lead confirmation from `core.release_jury()` and `jury.confirm_winners()`.
- Replace score summary loops with Mongo aggregation when idea volume becomes large.

## Local verification

Run setup, optional sample data, and tests with:

```powershell
python start_grit.py
```

Manual equivalent:

```powershell
python mongo_setup.py
python seed_sample_data.py
python -m unittest discover -s tests -v
```

## API evolution

Keep route behavior in `app/api.py` and update definitions in `app/openapi.py` in the same change. The current JSON API intentionally leaves binary image upload on the web form route.

## Security notes

- Never commit a live MongoDB URI or password. Use `.env`.
- Rotate the Flask `SECRET_KEY` for deployed environments.
- The public edit token is an ownership capability for the current version. Replace it with entrant authentication if the competition needs stronger identity controls.
- Uploaded files are limited by extension in this version. Add malware scanning and storage isolation for production.
