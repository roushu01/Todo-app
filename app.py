from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime, date
import secrets   # for generating secure key
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_dance.contrib.google import make_google_blueprint, google
import os
import warnings
warnings.filterwarnings("ignore", message=".*Scope has changed.*")
from flask_migrate import Migrate
from route_chart import chart_data
from collections import defaultdict
from flask_mail import Mail, Message


app = Flask(__name__)

import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Secure secret key
app.secret_key = os.getenv("SECRET_KEY")

# Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")

# Google OAuth config
app.config["GOOGLE_OAUTH_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
app.config["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for localhost testing

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

google_bp = make_google_blueprint(
    client_id=app.config["GOOGLE_OAUTH_CLIENT_ID"],
    client_secret=app.config["GOOGLE_OAUTH_CLIENT_SECRET"],
    scope=["openid",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email"],
    redirect_to="google_login_callback",
)
app.register_blueprint(google_bp, url_prefix="/login")





# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:root@localhost/Todo_app"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "signup" 
#User model
class User(db.Model, UserMixin):
    __tablename__ = "users" 

    id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email    = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

    todos = db.relationship('Todo', backref='user', lazy=True)


@app.route("/login/google/callback")
def google_login_callback():
    if not google.authorized:
        return redirect(url_for("google.login"))

    # Get user info from Google API
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        # flash(f"Failed to fetch user info: {resp.text}", "error")
        return redirect(url_for("login"))

    user_info = resp.json()
    print("Google User Info:", user_info)  # Debug

    # Safely extract data
    email = user_info.get("email")
    if not email:
        # flash("Google login failed — no email returned. Check your OAuth scopes.", "error")
        return redirect(url_for("login"))

    username = user_info.get("name", email.split("@")[0])

    # Check if user exists
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(username=username, email=email, password="google_auth_user")
        db.session.add(user)
        db.session.commit()

    login_user(user)
    # flash("Logged in with Google successfully!", "success")
    return redirect(url_for("create_todo"))




@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))
# Create a database model for the Todo item
class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    from_time = db.Column(db.String(50), nullable=False)
    to_time = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False)

    # Link to user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self) -> str:
        return f"{self.sno} - {self.title}"


with app.app_context():
    db.create_all()
# ----------------- Routes -----------------

@app.route("/send-task-mail")
@login_required
def send_task_mail():
    user_email = current_user.email

    tasks = Todo.query.filter_by(user_id=current_user.id, completed=False).all()

    if len(tasks) == 0:
        return "No pending tasks to send email"

    lines = []
    for t in tasks:
        lines.append(f"📌 {t.title} | {t.from_time} → {t.to_time}")

    body_msg = "\n".join(lines)

    msg = Message(
        subject="⏰ Your Task Schedule",
        sender=app.config['MAIL_USERNAME'],
        recipients=[user_email]
    )
    msg.body = f"Hello {current_user.username},\n\nHere are your pending tasks:\n\n{body_msg}\n\n✔ Complete them on time!\n\n— Task Manager App"

    mail.send(msg)
    return "Email sent successfully"


@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('create_todo'))  # logged-in users go to todo list
    else:
        return redirect(url_for('signup'))   
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        print("Signup Data:", username, email, password)

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered!", "error")
            return redirect(url_for("signup"))

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    # ⬇️ This must be at the same level as `if request.method == 'POST'`
    return render_template("Signup.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)  # ✅ log the user in
            flash("Login successful!", "success")
            return redirect(url_for("create_todo"))
        else:
            flash("Invalid credentials!", "error")
            return redirect(url_for("login"))

    return render_template("index.html", datetime=datetime)

@app.route('/todo', methods=['GET', 'POST'])
@login_required
def create_todo():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        from_time = request.form['from_time']
        to_time = request.form['to_time']
        date_created = request.form.get('date_created')  

        if date_created:
            date_created_obj = datetime.strptime(date_created, "%Y-%m-%d")
        else:
            date_created_obj = datetime.utcnow()

        todo = Todo(
            title=title,
            content=content,
            from_time=from_time,
            to_time=to_time,
            date_created=date_created_obj,
            user_id=current_user.id  # ✅ assign to logged-in user
        )

        db.session.add(todo)
        db.session.commit()
    
    today = date.today()
    
    # ✅ Only fetch todos for the current user
    count=Todo.query.filter_by(user_id=current_user.id).count()
    todays_todos = Todo.query.filter_by(user_id=current_user.id)\
                             .filter(db.func.date(Todo.date_created) == today)\
                             .all()

    return render_template('index.html', allTodo=todays_todos, today=today, datetime=datetime,count=count)

# Delete a todo
@app.route('/delete/<int:sno>')
def delete(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    if todo and todo.date_created.date() < date.today():
        flash("❌ Cannot delete past tasks!", "warning")
        return redirect(request.referrer or url_for("create_todo"))
    db.session.delete(todo)
    db.session.commit()
    return  redirect(request.referrer or url_for("create_todo"))


# Update a todo
@app.route('/update/<int:sno>', methods=['GET','POST'])
def update(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    if todo.date_created.date() < date.today():
        flash("❌ Cannot update past tasks!", "warning")
        return redirect(request.referrer or url_for("create_todo"))

    if request.method == 'POST':
        todo.title = request.form['title']
        todo.content = request.form['content']
        db.session.commit()
        return redirect("/")
    return render_template('update.html', todo=todo)


# Toggle completion
@app.route('/complete/<int:sno>', methods=['POST'])
@login_required
def complete(sno):
    todo = Todo.query.filter_by(sno=sno,user_id=current_user.id).first()
    todos = Todo.query.filter_by(completed=True,user_id=current_user.id).all()
    count_todos = len(todos)
    if todo and todo.date_created.date() < date.today():
        flash("❌ Cannot change status of past tasks!", "warning")
        return redirect(request.referrer or url_for("create_todo"))

    if todo:
        todo.completed = not todo.completed
        db.session.commit()

    return redirect(request.referrer or url_for("create_todo"))


# Calendar
@app.route('/calendar')
@login_required
def calendar():
    from route_chart import chart_data

    labels, data = chart_data(db, Todo, current_user.id)

    allTodo = Todo.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'calender.html',
        labels=labels,
        data=data,
        allTodo=allTodo
    )




@app.route('/events')
def events():
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    events = []
    for t in todos:
        events.append({
            "title": t.title,
            "start": t.date_created.strftime("%Y-%m-%d"),
            "extendedProps": {
                "description": t.content,
                "from_time": t.from_time,
                "to_time": t.to_time,
                "completed": t.completed
            },
            "color": "green" if t.completed else "navy",
            "textColor": "white",
            "borderColor": "white"
        })
    return jsonify(events)


@app.route('/todos_by_date/<date>')
@login_required
def todos_by_date(date):
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    todos = Todo.query.filter_by(user_id=current_user.id)\
        .filter(db.func.date(Todo.date_created) == selected_date).all()
    return jsonify([
        {
            "title": t.title,
            "content": t.content,
            "from_time": t.from_time,
            "to_time": t.to_time
        } for t in todos
    ])


@app.route("/tasks")
@login_required
def tasks():
    all_tasks = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.date_created.asc()).all()

    grouped_tasks = defaultdict(list)
    for t in all_tasks:
        task_date = t.date_created.date()
        grouped_tasks[task_date].append(t)

    grouped_tasks = dict(sorted(grouped_tasks.items()))

    count_todos = Todo.query.filter_by(user_id=current_user.id, completed=True).count()
    total_todo = Todo.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "task_list.html",
        grouped_tasks=grouped_tasks,
        count_todos=count_todos,
        total_todo=total_todo,
        today=date.today()
    )
@app.route("/chart-data")
@login_required
def chart_data_api():
    labels, data = chart_data(db, Todo, current_user.id)
    return jsonify({"labels": labels, "data": data})


@app.route('/pending')
def pending_tasks():
    todos = Todo.query.filter_by(completed=False,user_id=current_user.id).all()
    return render_template('task_list.html', allTodo=todos, title="Pending Tasks",date=date)

# @app.route('/')
# @login_required
# def count_completed_task():
#     # Fetch all todos for current user
#     todos = Todo.query.filter_by(user_id=current_user.id).all()
    
#     # Count completed ones
#     count_todos = Todo.query.filter_by(completed=True, user_id=current_user.id).count()

#     return render_template(
#         'task_list.html',
#         allTodo=todos,
#         title="All Tasks",
#         date=date,
#         count_todos=count_todos
#     )


@app.route('/completed')
@login_required
def completed_tasks():
    todos = Todo.query.filter_by(completed=True,user_id=current_user.id).all()
    return render_template('task_list.html', allTodo=todos, title="Completed Tasks",date=date)

# from route_chart import chart_bp
# app.register_blueprint(chart_bp)
# ----------------- Run -----------------
if __name__ == '__main__':

    app.run(debug=True)
