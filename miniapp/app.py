"""Lancer avec `make run`

Nouvel événement: http://localhost:5000/new-event-form
Liste des évenements: http://localhost:5000/events
Un événement: http://localhost:5000/event/1
"""

from flask import (
    Flask,
    make_response,
    request,
    jsonify,
    redirect,
    url_for,
    render_template,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import URL
from os import getenv


# Create Flask's `app` object
app = Flask(__name__)

app.config.update(
    dict(
        DATABASE_ADAPTER=getenv("DB_ADAPTER", "mysql+pymysql"),
        DATABASE_HOST=getenv("DB_HOST", "localhost"),
        DATABASE_USER=getenv("DB_USER", "miniapp"),
        DATABASE_PASS=getenv("DB_PASS", "secret"),
        DATABASE_SCHEMA=getenv("DB_SCHEMA", "miniapp"),
    )
)

app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
    app.config["DATABASE_ADAPTER"],
    username=app.config["DATABASE_USER"],
    password=app.config["DATABASE_PASS"],
    host=app.config["DATABASE_HOST"],
    database=app.config["DATABASE_SCHEMA"],
)

Base = type("Base", (DeclarativeBase,), {})
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class MiniappData(db.Model):
    """Exact translation of schema.sql"""

    __tablename__ = "miniapp_data"
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.CHAR(1))
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(
        db.TIMESTAMP,
        server_default=db.func.current_timestamp(),
        server_onupdate=db.func.current_timestamp(),
    )
    event = db.Column(db.CHAR(8))

    @property
    def as_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "event": self.event,
        }

    @property
    def as_smalldict(self):
        return {
            "id": self.id,
            "status": self.status,
            "url": url_for("handle_single_event", id=self.id),
        }


@app.route("/", methods=["GET"])
def homepage():
    if request.method != "GET":
        return make_response("Malformed request", 400)
    my_dict = {"what_to_see_here": "nothing", "check_rather": "/new-event-form"}
    headers = {"Content-Type": "application/json"}
    return make_response(jsonify(my_dict), 200, headers)


@app.route("/new-event-form", methods=["GET", "POST"])
def new_event_form():
    if request.method == "GET":
        return render_template("event/new.html")
    else:
        status = request.form.get("status")
        event_t = request.form.get("event")
        event = MiniappData(status=status, event=event_t)
        db.session.add(event)
        db.session.commit()
        return redirect(url_for("handle_single_event", id=event.id))


@app.route("/events", methods=["GET", "POST"])
def handle_events():
    if request.method not in ("GET", "POST"):
        return make_response("Bad request", 400)
    if request.method == "POST":
        body = request.get_json()
        event = MiniappData(
            status=body.get("status", "A"), event=body.get("event", "CREATE")
        )
        db.session.add(event)
        db.session.commit()
        return redirect(url_for("handle_single_event", id=event.id))
    else:
        event_list = db.session.execute(
            db.select(MiniappData).order_by(MiniappData.updated_at)
        ).scalars()
        return make_response(
            jsonify([d.as_smalldict for d in event_list]),
            200,
            {"Content-Type": "application/json"},
        )


@app.route("/events/<int:id>", methods=["GET", "DELETE", "PATCH"])
def handle_single_event(id):
    event = db.get_or_404(MiniappData, id)
    if request.method == "GET":
        return make_response(
            jsonify(event.as_dict), 200, {"Content-type": "application/json"}
        )
    elif request.method == "DELETE":
        db.session.delete(event)
        db.commit()
        return make_response(
            jsonify(
                dict(deleted=True, id=id), 200, {"Content-type": "application/json"}
            )
        )
    elif request.method == "PATCH":
        body = request.get_json()
        status = body.get("status")
        ev = body.get("event")
        touched = False
        if status:
            event.status = status
            touched = True
        if ev:
            event.event = ev
            touched = True
        if touched:
            db.session.commit()
            return redirect(url_for("handle_single_event", id=event.id))
        else:
            return make_response(
                dict(error="no changes for patch"),
                400,
                {"Content-type": "application/json"},
            )
    else:
        return make_response("Bad request", 400)


# populate the database
with app.app_context():
    app.logger.info("Populating dataabase")
    db.create_all()
    app.logger.info("Done populating dataabase")
