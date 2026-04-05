import os
import re
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = os.environ.get('SECRET_KEY', 'spotted_university_ultra_v8_final_fix') 
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///spotted.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PUBLIC_FOLDER'] = os.path.join(app.root_path, 'static', 'public')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)

@app.route('/public/')
def public_index():
    files = []
    for root, _, filenames in os.walk(app.config['PUBLIC_FOLDER']):
        rel_root = os.path.relpath(root, app.config['PUBLIC_FOLDER'])
        for name in filenames:
            rel_path = os.path.join(rel_root, name) if rel_root != '.' else name
            files.append(rel_path.replace('\\', '/'))
    return jsonify(sorted(files))

@app.route('/public/<path:filename>')
def public_files(filename):
    return send_from_directory(app.config['PUBLIC_FOLDER'], filename)

def br_time():
    return datetime.utcnow() - timedelta(hours=3)

@app.template_filter('mention')
def mention_filter(text):
    def replace_mention(match):
        username = match.group(1).lower()
        exists = User.query.filter_by(username=username).first()
        if exists:
            return f'<a href="/perfil/{username}" class="text-indigo-500 font-bold hover:underline">@{username}</a>'
        return f'@{username}' 
    return re.sub(r'@(\w+)', replace_mention, text)

def notify_mentions(content, sender_name, post_id):
    mentions = re.findall(r'@(\w+)', content)
    for username in mentions:
        user = User.query.filter_by(username=username.lower()).first()
        if user and user.id != session.get('user_id'):
            db.session.add(Notification(
                user_id=user.id, 
                sender_name=sender_name, 
                action_type="mencionou você em uma publicação", 
                post_id=post_id
            ))

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

post_likes = db.Table('post_likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'))
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True) 
    username = db.Column(db.String(80), unique=True, nullable=False) 
    password = db.Column(db.String(120), nullable=False)
    university = db.Column(db.String(50), nullable=True)
    bio = db.Column(db.String(150), default="Estudante no Spotted University 🎓")
    profile_pic = db.Column(db.String(200), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    notifications = db.relationship('Notification', backref='receiver', lazy=True, cascade="all, delete-orphan")
    followed = db.relationship('User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    liked_posts = db.relationship('Post', secondary=post_likes, backref=db.backref('liked_by', lazy='dynamic'))

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=br_time)
    likes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan")

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    content = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(80), default="Anônimo") 
    timestamp = db.Column(db.DateTime, default=br_time)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_name = db.Column(db.String(80))
    action_type = db.Column(db.String(100))
    post_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=br_time)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender_name = db.Column(db.String(80))
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=br_time)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    media_url = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=br_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    creator = db.relationship('User', backref='my_events')

with app.app_context():
    db.create_all()
    admin_master = User.query.filter_by(username='admin').first()
    if not admin_master:
        nova_senha_hash = generate_password_hash('Migo@2026!#')
        admin_master = User(name="Administrador", username='admin', password=nova_senha_hash, is_admin=True, bio="Sistema")
        db.session.add(admin_master)
    db.session.commit()

@app.route('/api/users')
def api_users():
    q = request.args.get('q', '').lower()
    if not q: return jsonify([])
    users = User.query.filter(User.username.like(f'{q}%'), User.is_admin == False).limit(5).all()
    return jsonify([{'username': u.username, 'name': u.name} for u in users])

@app.route('/')
def welcome():
    if 'user_id' in session: return redirect(url_for('feed'))
    return render_template('welcome.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').lower().strip()
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['name'] = user.name
        session['is_admin'] = user.is_admin
        session['profile_pic'] = user.profile_pic
        return redirect(url_for('feed'))
    flash('Usuário ou senha incorretos.')
    return redirect(url_for('welcome'))

@app.route('/registro', methods=['POST'])
def registro():
    name = request.form.get('name').strip()
    username = request.form.get('username').lower().strip()
    password = request.form.get('password')
    university = request.form.get('university')
    if " " in username:
        flash('O usuário não pode conter espaços.')
        return redirect(url_for('welcome'))
    if len(password) < 8 or not re.search(r"[!@#$%^&*()]", password):
        flash('Senha inválida.')
        return redirect(url_for('welcome'))
    if User.query.filter_by(username=username).first():
        flash('Login já existe.')
        return redirect(url_for('welcome'))
    user = User(name=name, username=username, password=generate_password_hash(password), university=university)
    db.session.add(user); db.session.commit()
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['name'] = user.name
    session['is_admin'] = False
    session['profile_pic'] = user.profile_pic 
    return redirect(url_for('feed'))

@app.route('/feed')
def feed():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template('index.html', posts=posts, unread_count=unread)

@app.route('/search')
def search():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    query = request.args.get('query', '').lower().strip().replace('@', '')
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    if not query:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
        return render_template('index.html', searching=True, posts=posts, unread_count=unread)
    results = User.query.filter(User.username.contains(query), User.is_admin == False).all()
    return render_template('index.html', search_results=results, query=query, searching=True, unread_count=unread)

@app.route('/postar', methods=['POST'])
def postar():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('content')
    anon_mode = request.form.get('anon_mode') == 'true'
    file = request.files.get('file'); filename = None
    if file and file.filename != '':
        ext = os.path.splitext(file.filename)[1]
        filename = str(uuid.uuid4()) + ext
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    new_post = Post(content=content, media_url=filename, user_id=session.get('user_id'), is_anonymous=anon_mode)
    db.session.add(new_post)
    db.session.flush() 
    if not anon_mode:
        notify_mentions(content, session.get('name'), new_post.id)
    db.session.commit()
    return redirect(url_for('feed'))

@app.route('/excluir_post/<int:post_id>')
def excluir_post(post_id):
    post = Post.query.get_or_404(post_id)
    if (post.user_id == session.get('user_id') and post.user_id is not None) or session.get('is_admin'):
        db.session.delete(post)
        db.session.commit()
    return redirect(request.referrer or url_for('feed'))

@app.route('/like/<int:post_id>')
def like(post_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    post = Post.query.get_or_404(post_id)
    user = User.query.get(session['user_id'])
    if post not in user.liked_posts:
        user.liked_posts.append(post)
        post.likes += 1
        if post.user_id and post.user_id != user.id:
            db.session.add(Notification(user_id=post.user_id, sender_name=user.name, action_type="curtiu sua publicação", post_id=post.id))
    else:
        user.liked_posts.remove(post)
        post.likes -= 1
    db.session.commit()
    return redirect(url_for('feed', _anchor=f"post-{post_id}"))

@app.route('/comentar/<int:post_id>', methods=['POST'])
def comentar(post_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('comment_content'); post = Post.query.get_or_404(post_id)
    if content:
        autor_username = session.get('username') 
        db.session.add(Comment(content=content, post_id=post_id, username=autor_username))
        if post.user_id and post.user_id != session.get('user_id'):
            db.session.add(Notification(user_id=post.user_id, sender_name=session.get('name'), action_type="comentou sua publicação", post_id=post.id))
        notify_mentions(content, session.get('name'), post.id)
        db.session.commit()
    return redirect(url_for('feed', _anchor=f"post-{post_id}"))

@app.route('/perfil/<username>')
def perfil(username):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    user = User.query.filter_by(username=username).first_or_404()
    if user.is_admin and not session.get('is_admin'): return redirect(url_for('feed'))
    posts = Post.query.filter_by(user_id=user.id, is_anonymous=False).order_by(Post.timestamp.desc()).all()
    messages = Message.query.filter_by(receiver_id=user.id).order_by(Message.timestamp.desc()).all()
    me = User.query.get(session['user_id'])
    return render_template('profile.html', user=user, posts=posts, messages=messages, me=me)

@app.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    user = User.query.get(session['user_id'])
    name_post = request.form.get('name')
    university_post = request.form.get('university')
    bio_post = request.form.get('bio')
    if name_post:
        user.name = name_post[:80]
        session['name'] = user.name
    if university_post: user.university = university_post[:50]
    if bio_post is not None: user.bio = bio_post[:150]
    file = request.files.get('profile_pic')
    if file and file.filename != '':
        ext = os.path.splitext(file.filename)[1]
        filename = f"pfp_{user.id}_{str(uuid.uuid4())[:8]}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.profile_pic = filename
        session['profile_pic'] = filename 
    db.session.commit()
    return redirect(url_for('perfil', username=user.username))

@app.route('/seguir/<username>')
def seguir(username):
    if 'user_id' not in session: return redirect(url_for('perfil', username=username))
    user_to_follow = User.query.filter_by(username=username).first_or_404()
    me = User.query.get(session['user_id'])
    if user_to_follow.id != me.id:
        if not me.is_following(user_to_follow):
            me.followed.append(user_to_follow)
            db.session.add(Notification(user_id=user_to_follow.id, sender_name=me.name, action_type="começou a te seguir"))
        else:
            me.followed.remove(user_to_follow)
        db.session.commit()
    return redirect(url_for('perfil', username=username))

@app.route('/enviar_recado/<int:user_id>', methods=['POST'])
def enviar_recado(user_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('content')
    if content:
        sender = session.get('name')
        db.session.add(Message(receiver_id=user_id, sender_name=sender, content=content))
        db.session.add(Notification(user_id=user_id, sender_name=sender, action_type="deixou um recado no mural"))
        db.session.commit()
    return redirect(url_for('perfil', username=User.query.get(user_id).username))

@app.route('/notificacoes')
def notificacoes():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.timestamp.desc()).all()
    for n in notifs: n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)

@app.route('/eventos')
def eventos():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    all_events = Event.query.order_by(Event.created_at.desc()).all()
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template('eventos.html', events=all_events, unread_count=unread)

@app.route('/criar_evento', methods=['POST'])
def criar_evento():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    title = request.form.get('title')
    description = request.form.get('description')
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')
    
    file = request.files.get('file'); filename = None
    if file and file.filename != '':
        ext = os.path.splitext(file.filename)[1]
        filename = str(uuid.uuid4()) + ext
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    full_date = f"{date} às {time}"
    new_event = Event(title=title, description=description, event_date=full_date, location=location, media_url=filename, user_id=session['user_id'])
    db.session.add(new_event)
    
    # Criar postagem no feed automaticamente
    event_content = f"📢 NOVO EVENTO: {title}\n📍 Local: {location}\n📅 Data: {full_date}\n\n{description}\n\nCriado por @{session['username']}"
    feed_post = Post(content=event_content, media_url=filename, user_id=session['user_id'], is_anonymous=False)
    db.session.add(feed_post)
    
    db.session.commit()
    return redirect(url_for('eventos'))

@app.route('/excluir_evento/<int:event_id>')
def excluir_evento(event_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    event = Event.query.get_or_404(event_id)
    if event.user_id == session['user_id'] or session.get('is_admin'):
        db.session.delete(event)
        db.session.commit()
    return redirect(url_for('eventos'))

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('welcome'))

if __name__ == '__main__':
    app.run(debug=True)