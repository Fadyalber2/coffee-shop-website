import pytest
import os
import tempfile
from app import app as flask_app, db

@pytest.fixture(scope="session")
def app():
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp()

    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        "SESSION_TYPE": "filesystem",
        "SERVER_NAME": "localhost" # Force localhost
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture(autouse=True)
def reset_db(app):
    """Reset database for each test."""
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
