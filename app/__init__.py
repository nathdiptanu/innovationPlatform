from flask import Flask, render_template
from werkzeug.exceptions import Forbidden, NotFound

from .auth import auth_bp
from .config import Config
from .core import core_bp
from .db import close_db, init_app as init_db_app
from .jury import jury_bp
from .public import public_bp
from .api import api_bp
from .entitlements import can_access


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(jury_bp)
    app.register_blueprint(api_bp)
    app.jinja_env.globals["can_access"] = can_access
    init_db_app(app)
    app.teardown_appcontext(close_db)

    @app.errorhandler(Forbidden)
    def forbidden(error):
        return render_template("error.html", code=403, message=str(error)), 403

    @app.errorhandler(NotFound)
    def not_found(error):
        return render_template("error.html", code=404, message=str(error)), 404

    return app
