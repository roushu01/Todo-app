from datetime import date

def chart_data(db, Todo, user_id):
    today = date.today()

    completed = db.session.query(Todo)\
        .filter(Todo.user_id == user_id)\
        .filter(db.func.date(Todo.date_created) == today)\
        .filter(Todo.completed == True)\
        .count()

    incomplete = db.session.query(Todo)\
        .filter(Todo.user_id == user_id)\
        .filter(db.func.date(Todo.date_created) == today)\
        .filter(Todo.completed == False)\
        .count()

    labels = ["Completed", "Incomplete"]
    data = [completed, incomplete]

    return labels, data
