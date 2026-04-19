from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config


db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes import user_routes, student_routes, course_routes, score_routes, query_routes
    app.register_blueprint(user_routes.bp)
    app.register_blueprint(student_routes.bp)
    app.register_blueprint(course_routes.bp)
    app.register_blueprint(score_routes.bp)
    app.register_blueprint(query_routes.bp)

    return app
