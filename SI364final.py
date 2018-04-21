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
from wtforms import StringField, SubmitField, ValidationError # Note that you may need to import more here! Check out examples that do what you want to figure out what.
from wtforms.validators import Required, Length # Here, too
from flask_migrate import Migrate, MigrateCommand
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

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

## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)


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


def get_face(db_session,user_name):
    pass

def create_face(db_session, face_id):
    pass

def get_pin():
    pass

def create_pin():
    pass


##################
##### MODELS #####
##################

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer,primary_key=True)
    user = db.Column(db.String(256)) #, unique=True)
    face = db.Column(db.String(256)) #, unique=True)
    #pin = db.Column(db.Integer)
    def __repr__(self):
        return "{} {}".format(self.id, self.user)

class Pin(db.Model):
    __tablename__ = "pins"
    id = db.Column(db.Integer,primary_key=True)
    number = db.Column(db.Integer)
    def __repr__(self):
        return "{} {}".format(self.id, self.number)


###################
###### FORMS ######
###################
class UserForm(FlaskForm):
    user = StringField("Please enter your username.",validators=[Required()])
    face = FileField("Insert a photo with your face",validators=[FileRequired()])
    submit = SubmitField()

#more to be done


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
            return render_template("login_success.html",target_image=full_filename1, source_image = full_filename2, similarity = similarity)
    return render_template("index.html", form = form)

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

#For checking if file upload is succesful
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)



## Code to run the application...




if __name__ == '__main__':
    db.create_all()
    app.run(use_reloader=True,debug=True)
# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!



