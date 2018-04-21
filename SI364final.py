#import required libraries
import os
import requests
import json
import boto3
import flask
from flask import Flask, render_template, session, redirect, url_for, flash, request, send_from_directory
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
from wtforms import SelectMultipleField,BooleanField, StringField, SubmitField, ValidationError # Note that you may need to import more here! Check out examples that do what you want to figure out what.
from wtforms.validators import Required, Length # Here, too
from flask_migrate import Migrate, MigrateCommand
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Imports for login management
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
UPLOAD_FOLDER = 'uploads'

## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True

## All app.config values
app.config['SECRET_KEY'] = 'si364randomsecretkeyhardtoguess'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/SI364projectplanhongjisu"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set up Flask debug and necessary additions to app
manager = Manager(app)
db = SQLAlchemy(app) # For database use
migrate = Migrate(app, db) # For database use/updating
manager.add_command('db', MigrateCommand) # Add migrate command to manager

# Login configurations setup
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app) # set up login manager


## Set up Shell context so it's easy to use the shell to debug
# Define function
def make_shell_context():
    return dict( app=app, db=db)
# Add function use to manager
manager.add_command("shell", Shell(make_context=make_shell_context))

## NOTE ON MIGRATION SETUP
## You will get the following message when running command to create migration folder, e.g.:
## python main_app.py db init
## -->
# Please edit configuration/connection/logging settings in ' ... migrations/alembic.ini' before proceeding
## This is what you are supposed to see!

#########
######### Everything above this line is important/useful setup, not mostly application-specific problem-solving.
#########

######################################
######## HELPER FXNS (If any) ########
######################################

def get_user(db_session,user_in):
    search_user = db_session.query(User).filter_by(user=user_in).first()
    if search_user:
        return search_user

def create_user(db_session, user_in, face_in):
    search_user = db_session.query(User).filter_by(user=user_in).first()
    if search_user:
        return 0
    new_user = User(user=user_in,face=face_in)
    db_session.add(new_user)
    db_session.commit()
    return new_user

def update_user(db_session, face_in):
    
    return update_user

def face_detect(imageFile1, imageFile2):
    sourceFile= open(imageFile1, 'rb')
    targetFile= open(imageFile2, 'rb')
    
    client=boto3.client('rekognition','us-east-2')
    
    response=client.compare_faces(SimilarityThreshold=70,
                                  SourceImage={'Bytes': sourceFile.read()},
                                  TargetImage={'Bytes': targetFile.read()})

    #return flask.jsonify(**response)
    for faceMatch in response['FaceMatches']:
        return str(faceMatch['Similarity'])
    return "0"

def image_detect(imageFile):
    image = open(imageFile, 'rb')
    client=boto3.client('rekognition','us-east-2')
    response = client.detect_labels(
                                    Image={'Bytes': image.read()},
                                    MaxLabels=20,
                                    MinConfidence=70
                                    )
    return response['Labels']

def get_article_by_id(id):
    """returns article or None"""
    article_obj = Article.query.filter_by(id=id).first()
    return article_obj

def get_or_create_search(db_session, f):
    filename = f.filename
    searchTerm = db_session.query(Search).filter_by(term=filename).first()
    if searchTerm:
        print("Found term")
        return searchTerm
    else:
        print("Added term")
        full_filename = os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(filename))
        f.save(full_filename)
        result_list = image_detect(full_filename)
        searchTerm = Search(term=filename)
        for label in result_list:
            output = label['Name'] + " : " + str(label['Confidence']) + "%\n"
            flash (output)
            result = get_or_create_result(db_session, filename, label['Name'], str(label['Confidence']))
            searchTerm.results.append(result)
        db_session.add(searchTerm)
        db_session.commit()
        return searchTerm

def get_or_create_result(db_session, term_in, key_in, value_in):
    result = db_session.query(Result).filter_by(term = term_in, key = key_in, value = value_in).first()
    if result:
        return result
    else:
        result = Result(term = term_in, key = key_in, value = value_in)
        db_session.add(result)
        db_session.commit()
        return result

def get_or_create_personal_collection(db_session, name, search_list, current_user):
    searchCollection = PersonalCollection(name = name,user_id=current_user.id,searches=[])
    for a in search_list:
        searchCollection.searches.append(a)
    db_session.add(searchCollection)
    db_session.commit()
    return searchCollection


def get_search_by_id(id):
    """returns article or None"""
    search_obj = Search.query.filter_by(id=id).first()
    return search_obj

##################
##### MODELS #####
##################

# Set up association Table between Articles and collections prepared by user
tags = db.Table('tags',db.Column('search_id',db.Integer, db.ForeignKey('search.id')),db.Column('result_id',db.Integer, db.ForeignKey('results.id')))

user_collection = db.Table('user_collection',db.Column('user_id', db.Integer, db.ForeignKey('search.id')),db.Column('collection_id',db.Integer, db.ForeignKey('personalCollections.id')))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer,primary_key=True)
    user = db.Column(db.String(256), unique=True)
    def validate_user(form, field):
        if len(field.data) > 256:
            raise ValidationError('Name must be less than 256 characters')
    face = db.Column(db.String(256), unique=True)
    def validate_face(form, field):
        if len(field.data) > 256:
            raise ValidationError('Name must be less than 256 characters')
    collection = db.relationship('PersonalCollection', backref='User')
    #pin = db.Column(db.Integer)
    def __repr__(self):
        return "{} {}".format(self.id, self.user)


class PersonalCollection(db.Model):
    __tablename__ = "personalCollections"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    searches = db.relationship('Search',secondary=user_collection,backref=db.backref('personalCollections',lazy='dynamic'),lazy='dynamic')

class Result(db.Model):
    __tablename__ = "results"
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(256))
    key = db.Column(db.String(128))
    value = db.Column(db.String(256))
    def __repr__(self):
        return "{}, {}, Confidence: {}".format(self.term, self.key,self.value)


class Search(db.Model):
    __tablename__ = "search"
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(256),unique=True) # Only unique searches
    results = db.relationship('Result',secondary=tags,backref=db.backref('search',lazy='dynamic'),lazy='dynamic')
    
    def __repr__(self):
        return "{} : {}".format(self.id, self.term)


## DB load functions
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) # returns User object or None

###################
###### FORMS ######
###################
class UserForm(FlaskForm):
    user = StringField("Please enter your username.",validators=[Required()])
    face = FileField("Insert a photo with your face",validators=[FileRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField()

class SearchForm(FlaskForm):
    search = FileField("Insert a photo you want to know about",validators=[FileRequired()])
    submit = SubmitField('Submit')

class UpdateForm(FlaskForm):
    new_face = FileField("Insert a photo of a new face", validators=[FileRequired()])
    submit = SubmitField()

class CollectionCreateForm(FlaskForm):
    name = StringField('Collection Name',validators=[Required()])
    search_picks = SelectMultipleField('Searches to include')
    submit = SubmitField("Create Collection")

class DeleteButtonForm(FlaskForm):
    submit = SubmitField("Delete")

#######################
###### VIEW FXNS ######
#######################


## Error handling routes
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

## Main route

@app.route('/', methods=['GET', 'POST'])
def index():
    # Initialize the form
    form = UserForm()
    if form.validate_on_submit():
        check_user = get_user(db.session, form.user.data)
        if check_user is None:
            flash("user is not registered")
        else:
            f1 = form.face.data
            filename1 = secure_filename(f1.filename)
            full_filename1 = os.path.join(app.config['UPLOAD_FOLDER'],filename1)
            f1.save(full_filename1)
            filename2 = secure_filename(check_user.face)
            full_filename2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)
            similarity = face_detect(full_filename1,full_filename2)
            if similarity == "0":
                flash("You did not pass the validation. Try a different picture")
            else:
                login_user(check_user)
            return render_template("login_success.html",target_image=full_filename1, source_image = full_filename2, similarity = similarity)
    return render_template("index.html", form = form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        get_or_create_search(db.session, form.search.data)
    return render_template("search.html", form=form)

@app.route('/update', methods=['GET', 'POST'])
@login_required
def update():
    form = UpdateForm()
    if form.validate_on_submit():
        f = form.new_face.data
        update_user = db.session.query(User).filter_by(user=current_user.user).first()
        filename = f.filename
        full_filename = os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(filename))
        f.save(full_filename)
        update_user.face = filename
        db.session.add(update_user)
        db.session.commit()
        return redirect(url_for('register_success', full_filename = full_filename))
    return render_template("update.html", form=form)

@app.route('/create_search_collection',methods=["GET","POST"])
@login_required
def create_searchlist():
    form = CollectionCreateForm()
    choices = []
    for a in Search.query.all():
        choices.append((a.id, a.term))
    form.search_picks.choices = choices
    if request.method == 'POST':
        search_selected = form.search_picks.data # list?
        print("SELECTED", search_selected)
        search_objects = [get_search_by_id(int(id)) for id in search_selected]
        print("RETURNED", search_objects)
        get_or_create_personal_collection(db.session,name=form.name.data,current_user=current_user,search_list=search_objects) # How to access user, here and elsewhere TODO
        return redirect(url_for('all_collections'))
    return render_template('create_search_collection.html',form=form)

@app.route('/view_collection',methods=["GET","POST"])
@login_required
def all_collections():
    form = DeleteButtonForm()
    all_collections = [] # To be tuple list of title, genre
    collections = PersonalCollection.query.all()
    print (collections)
    for s in collections:
        collect_user = db.session.query(User).filter_by(id=s.user_id).first()
        all_collections.append((collect_user.user,s.name))
    return render_template('all_collections.html',all_collections=all_collections, form=form)

@app.route('/delete/<lst>',methods=["GET","POST"])
def delete(lst):
    tobedeleted = PersonalCollection.query.filter_by(name=lst).first()
    db.session.delete(tobedeleted)
    db.session.commit()
    flash('Deleted list {}'.format(tobedeleted.name))
    return redirect(url_for('all_collections'))

@app.route('/addUser', methods=['GET', 'POST'])
def add_users():
    form = UserForm()
    if form.validate_on_submit():
        if get_user(db.session, form.user.data) is None:
            f = form.face.data
            filename = secure_filename(f.filename)
            create_user(db.session, form.user.data,filename)
            full_filename = os.path.join(app.config['UPLOAD_FOLDER'],filename)
            f.save(full_filename)
            #to check if file is uploaded correctly
            #return redirect(url_for('uploaded_file',filename=filename))
            flash("register success click Home to login")
            return redirect(url_for('register_success', full_filename = full_filename))
        else:
            flash("try using a different username or different filename. Username&Filname must be Unique")
    return render_template("add_user.html",form = form)


@app.route('/regSuccess', methods=['GET', 'POST'])
def register_success():
    return render_template("register_success.html", user_image = request.args.get('full_filename'))


@app.route('/allUsers')
def all_users():
    all_users = [] # To be tuple list of title, genre
    users = User.query.all()
    for s in users:
        all_users.append((s.user,s.face))
    return render_template('all_users.html',all_users=all_users)

#For checking if file upload is succesful
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['face']
        f.save(secure_filename(f.filename))
        return 'file uploaded successfully'

#For checking if file upload is successful
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

#For checking if user is logged in
@app.route('/secret')
@login_required
def secret():
    return "Only authenticated users can do this! Try to log in or contact the site admin."

## Code to run the application...




if __name__ == '__main__':
    db.create_all()
    app.run(use_reloader=True,debug=True)
# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!



