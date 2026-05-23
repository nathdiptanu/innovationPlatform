from app import create_app
from app.services import bootstrap_defaults


app = create_app()


with app.app_context():
    bootstrap_defaults()
    print("GRIT MongoDB collections/indexes are ready and bootstrap core user is created when configured.")
