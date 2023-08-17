from flask import Flask, render_template, request, redirect, flash,url_for,jsonify
from flask_login import login_required, current_user, LoginManager, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import abort
from datetime import datetime, timedelta, time
import os
import re
from models import MyUser, Notes, db

app = Flask(__name__, static_url_path='/static')
app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return MyUser.select().where(MyUser.id == int(user_id)).first()


@app.before_request
def before_request():
    db.connect()

    
@app.after_request
def after_request(response):
    db.close()
    return response


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        user = MyUser.select().where(MyUser.email==email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect('/login/')
        else:
            login_user(user)
            return redirect('/')
    return render_template('login.html')


@app.route('/logout/')
def logout():
    logout_user()
    return redirect('/login/')


def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    return True


@app.route('/register/', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        user = MyUser.select().where(MyUser.email == email).first()
        if user:
            flash('email address already exists')
            return redirect('/register/')
        if MyUser.select().where(MyUser.username == username).first():
            flash('username already exists')
            return redirect('/register/')
        else:
            if validate_password(password):
                MyUser.create(
                    email=email,
                    username=username,
                    password=generate_password_hash(password),
                )
                return redirect('/login/')
            else:
                flash('wrong password')
                return redirect('/register/')
    return render_template('register.html')


@app.route('/new_note', methods=['GET', 'POST','DELETE'])
@login_required
def new_note():
    if request.method == 'POST':
        notes_name = request.form['title']
        content = request.form['content']
        days_to_delete = request.form.get('days_to_delete')
        time_to_delete = request.form.get('time_to_delete')

        note = Notes(notes_name=notes_name, content=content, author=current_user)

        if days_to_delete and time_to_delete:
            current_time = datetime.now().time()
            time_to_delete_obj = datetime.strptime(time_to_delete, '%H:%M').time()

            if current_time <= time_to_delete_obj:
                expiration_date = datetime.now() + timedelta(days=int(days_to_delete), hours=time_to_delete_obj.hour, minutes=time_to_delete_obj.minute)
            else:
                expiration_date = datetime.now() + timedelta(days=int(days_to_delete) + 1, hours=time_to_delete_obj.hour, minutes=time_to_delete_obj.minute)

            note.days_to_delete = int(days_to_delete)
            note.time_to_delete = time_to_delete_obj
            note.expiration_date = expiration_date

            if expiration_date == 0:
                return delete_note(note)

        note.save()

        return redirect('/')

    return render_template('new_note.html')

@app.route('/pin_note/<int:note_id>/', methods=['POST'])
@login_required
def toggle_pin(note_id):
    note = Notes.get_or_none(id=note_id)
    if not note or note.author_id != current_user.id:
        return jsonify({'success': False, 'message': 'Ошибка закрепления заметки.'})

    note.pinned = not note.pinned
    note.save()

    return jsonify({'success': True, 'message': 'Заметка успешно закреплена/откреплена!'})

@app.route('/search_notes', methods=['GET'])
@login_required
def search_notes():
    search_title = request.args.get('title')
    user_notes = Notes.select().where(
        (Notes.author == current_user) & (Notes.notes_name.contains(search_title))
    )

    notes_data = []
    for note in user_notes:
        note_data = {
            'id': note.id,
            'notes_name': note.notes_name,
            'content': note.content,
            'pinned': note.pinned
        }

        if note.expiration_date:
            expiration_timestamp = int(note.expiration_date.timestamp())
            note_data['expiration_date'] = expiration_timestamp

        notes_data.append(note_data)

    return jsonify(notes_data)



@app.route('/update_profile/', methods=['GET', 'PATCH'])    
@login_required
def update_profile():
    user_notes = Notes.select().where(Notes.author == current_user)
    
    if request.method == 'PATCH':
        data = request.json

        new_username = data.get('new_username')
        new_email = data.get('new_email')
        new_password = data.get('new_password')
        current_password = data.get('current_password')

        current_user.username = new_username
        current_user.email = new_email

        if new_password and validate_password(new_password):
            current_user.password = generate_password_hash(new_password)

        current_user.save()

        return jsonify({'success': True, 'message': 'Профиль успешно обновлен!'})

    return render_template('profile.html', current_user=current_user, user_notes=user_notes)



@app.route('/edit_note/<int:note_id>/', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    try:
        note = Notes.get(Notes.id == note_id, Notes.author == current_user)
    except Notes.DoesNotExist:
        abort(404)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        note.notes_name = title
        note.content = content
        note.save()
        flash('Заметка успешно обновлена!', 'success')
        return redirect('/')

    return render_template('edit_note.html', note=note)


@app.route('/delete_note/<int:note_id>', methods=['POST','DELETE'])
@login_required
def delete_note(note_id):
    note = Notes.get_or_none(id=note_id)
    if note and note.author_id == current_user.id:
        note.delete_instance()
        flash('Заметка успешно удалена!', 'success')
    else:
        flash('Ошибка удаления заметки.', 'error')
    return redirect('/')


@app.route('/')
def home():
    if current_user.is_authenticated:
        user_notes = Notes.select().where(Notes.author_id == current_user.id)
        return render_template('home.html', notes=user_notes)
    else:
        return render_template('home.html', notes=[])


if __name__ == '__main__':
    app.run(debug=True)




        # if not new_username or not new_email or not current_password:
        #     return jsonify({'success': False, 'message': 'Неверные данные. Обновление профиля не выполнено.'}) 

        # if not check_password_hash(current_user.password, current_password):
        #     return jsonify({'success': False, 'message': 'Неверный текущий пароль. Обновление профиля не выполнено.'})