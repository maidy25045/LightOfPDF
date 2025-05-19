from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from slugify import slugify
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

mongo = PyMongo(app)
db = mongo.cx[app.config['DATABASE_NAME']]


# Fixed data
MODES = ['academic', 'admission']

SUBJECTS = [
    "physics 1st paper",
    "physics 2nd paper",
    "chemistry 1st paper",
    "chemistry 2nd paper",
    "math 1st paper",
    "math 2nd paper",
    "biology 1st paper",
    "biology 2nd paper",
    "english 1st paper",
    "bangla 1st paper",
    "bangla 2nd paper",
    "ict"
]

# Helper: Validate mode and subject
def valid_mode(mode):
    return mode.lower() in MODES

def valid_subject(subject):
    return subject.lower() in SUBJECTS

# Helper: Generate slug filename from title
def generate_slug(title):
    return slugify(title)

# Routes

@app.route('/')
def home():
    return render_template('home.html', modes=MODES)

@app.route('/<mode>')
def mode_page(mode):
    mode = mode.lower()
    if not valid_mode(mode):
        return render_template('error.html', message='Invalid Mode'), 404
    # Show all subjects as cards
    return render_template('mode.html', mode=mode, subjects=SUBJECTS)

@app.route('/<mode>/<subject>')
def subject_page(mode, subject):
    mode = mode.lower()
    subject = subject.lower()
    if not valid_mode(mode) or not valid_subject(subject):
        return render_template('error.html', message='Invalid Mode or Subject'), 404

    # No need to check db.modes — you're not using that collection
    pdfs = list(db.pdfs.find({'mode': mode, 'subject': subject}))
    return render_template('subject.html', mode=mode, subject=subject, pdfs=pdfs)


@app.route('/pdf/<subject>/<filename>')
def pdf_view(subject, filename):
    subject = subject.lower()
    if not valid_subject(subject):
        return render_template('error.html', message='Invalid Subject'), 404
    pdf = db.pdfs.find_one({'subject': subject, 'filename': filename})
    if not pdf:
        return render_template('error.html', message='PDF not found'), 404
    return render_template('pdf_view.html', pdf=pdf)

# Admin Authentication

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['admin_logged_in'] = True
            flash('Logged in successfully.', 'success')
            return redirect(url_for('upload'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out.', 'info')
    return redirect(url_for('home'))

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/upload', methods=['GET', 'POST'])
@admin_required
def upload():
    if request.method == 'POST':
        mode = request.form.get('mode', '').lower()
        subject = request.form.get('subject', '').lower()
        title = request.form.get('title', '').strip()
        link = request.form.get('link', '').strip()
        description = request.form.get('description', '').strip()
        photo = request.form.get('photo', '').strip()

        # Validation
        errors = []
        if not valid_mode(mode):
            errors.append('Invalid mode selected.')
        if not valid_subject(subject):
            errors.append('Invalid subject selected.')
        if not title:
            errors.append('Title is required.')
        if not link:
            errors.append('Link is required.')
        
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('upload.html', modes=MODES, subjects=SUBJECTS, form=request.form)

        filename = generate_slug(title)

        # Check if already exists
        exists = db.pdfs.find_one({'filename': filename, 'subject': subject, 'mode': mode})
        if exists:
            flash('A PDF with this title already exists for this subject and mode.', 'danger')
            return render_template('upload.html', modes=MODES, subjects=SUBJECTS, form=request.form)

        # Insert into DB
        pdf_data = {
            'mode': mode,
            'subject': subject,
            'title': title,
            'filename': filename,
            'link': link,
            'description': description,
            'photo': photo,
        }
        db.pdfs.insert_one(pdf_data)
        flash('PDF metadata uploaded successfully!', 'success')
        return redirect(url_for('subject_page', mode=mode, subject=subject))
    
    return render_template('upload.html', modes=MODES, subjects=SUBJECTS)


@app.route('/search')
def search():
    query = request.args.get('query', '').strip()
    if not query:
        return render_template('search_results.html', results=[], query=query)

    # Case-insensitive search across title, subject, and description
    search_filter = {
        "$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"subject": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
        ]
    }

    results = list(db.pdfs.find(search_filter))
    return render_template('search_results.html', results=results, query=query)




# Error handlers

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message='Page not found (404)'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html', message='Internal server error (500)'), 500

if __name__ == '__main__':
    app.run(debug=True)
