from app import create_app
from app.db import collection
from app.services import bootstrap_defaults
from seed_sample_data import seed


def prepare_app():
    app = create_app()
    with app.app_context():
        bootstrap_defaults()
        if collection("ideas").count_documents({}) == 0:
            seed()
    return app


if __name__ == "__main__":
    prepare_app().run(debug=False)
