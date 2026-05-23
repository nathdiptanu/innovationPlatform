from app import create_app
from app.services import bootstrap_defaults
from seed_sample_data import seed


def prepare_app():
    app = create_app()
    with app.app_context():
        bootstrap_defaults()
        seed()
    return app


if __name__ == "__main__":
    prepare_app().run(debug=False)
