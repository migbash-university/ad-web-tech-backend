# -*- coding: utf-8 -*-
# !flask/bin/Python

import base64
import logging
import json
import requests
# import dns
# ---
from instance import email, mongodb_name, mongodb_uri, password
# ---
from flask import Flask, jsonify, render_template, request
from flask_restful import Api, Resource
from flask_cors import CORS
# ---
import firebase_admin
from firebase_admin import firestore, credentials, auth
# ---
from flask_mail import Mail, Message

# ~~~~~~~~~~ Init APP ~~~~~~~~~~
app = Flask(__name__)
api = Api(app)
CORS(app)

# ~~~~~~~~~~ Flask FIrebase (Firestore) Config ~~~~~~~~~~
cred = credentials.Certificate("./arkvision-space-firebase-adminsdk-1x9dn-242ba9ae7e.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ~~~~~~~~~~ Flask MongoDB Config ~~~~~~~~~~
# app.config['MONGO_DBNAME'] = mongodb_name
# app.config['MONGO_URI'] = mongodb_uri
# mongo = PyMongo(app)

# ~~~~~~~~~~ FLask_Mail Config ~~~~~~~~~~
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = email
app.config['MAIL_PASSWORD'] = password
mail = Mail(app)

# ~~~~~~~~~~ FLASK LOGGER ~~~~~~~~~~
app.logger.setLevel(logging.INFO)

# ~~~~~~ FLASK OTHER CONFIG ~~~~~~~~
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.url_map.strict_slashes = False

@app.route('/news_sub', methods=['POST'])
def email():
  # email_txt = request.form['email']
  welcome_email = Message("Welcome to ArkVision", sender='infospaceshadow@gmail.com', recipients=['miguelbacharov20@gmail.com'])
  welcome_email.html = '<h1> Thank you for subscribing to us! </h1> <hr> <p> We hope you will continue with us in our exciting journey into the future of Fintech & Blockchain! We have much exciting stuff planned for the future, and we would like you to be a part of it! 🤗 </p> <p> ☺️ Help us grow by mentioning us to your friends or via social media. </p> <p> Stay tuned on our social media platforms to keep up-to-date with us and our progress! </p> <hr> <br> <p> For any questions, please email us to contactus@napierfintech.com 24/7 </p> <p> If you consider sponsoring us ❤️, please email us to napierblockchain@gmail.com 24/7 </p> <br> <p> Fintech & Blockchain Society | Edinburgh Napier Univeristy | <b> Striving for Future Knowledge </b> </p>'                                                        #Customize based on user input
  mail.send(welcome_email)
  return "Success"

@app.route('/email_notif', methods=['POST'])
def email_notif():
  """
    email_notif(): Subscribes the user to an Email Notification update for a particular launch for 15min. before launch
  """
  try:
    data = request.json
    if app.debug:
        app.logger.info(data)
    return 'Email has been sent and notifications has been enabled'

  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/chat', methods=['GET', 'POST'])
def chat():
  """
  chat(): Fetches document from Firestore collection as JSON
  chat: returns data for the particular launch
  """
  try:
    data = request.data
    # Get target chat data for launch_id
    launch_id = data 
    # Only users are allowed to chat
    user_uid = data
    # decoded = auth.verify_id_token(token)
    # uid = decoded.uid
    doc_ref = db.collection(u'chat').document(u'aszxcz-1231')
    # chat = doc_ref.stream()
    chat = doc_ref.get()
    if chat.exists:
        print(f'Document data: {chat.to_dict()}')
        return chat.to_dict()
    else:
        print(u'No such document!')
        return 'No such document!'

  except Exception as e:
    return f"An Error Occured: {e}"

# =====
# USER ENDPOINTS
# ====

def verif_email(email, email_link):
  welcome_email = Message("Please Verify your Email", sender='infospaceshadow@gmail.com', recipients=[email])
  welcome_email.html = '<h1> Thank you for subscribing to us! </h1> <hr>' + email_link + '<p> We hope you will continue with us in our exciting journey into the future of Fintech & Blockchain! We have much exciting stuff planned for the future, and we would like you to be a part of it! 🤗 </p> <p> ☺️ Help us grow by mentioning us to your friends or via social media. </p> <p> Stay tuned on our social media platforms to keep up-to-date with us and our progress! </p> <hr> <br> <p> For any questions, please email us to contactus@napierfintech.com 24/7 </p> <p> If you consider sponsoring us ❤️, please email us to napierblockchain@gmail.com 24/7 </p> <br> <p> Fintech & Blockchain Society | Edinburgh Napier Univeristy | <b> Striving for Future Knowledge </b> </p>'                                                        #Customize based on user input
  mail.send(welcome_email)
  if app.debug:
    app.logger.info('Email Send successfully to ' + email)
  return

def reset_password(email, reset_link):
  _email = Message('Password Reset Link', sender='infospaceshadow@gmail.com', recipients=[email])
  _email.html = '<h1> Do not worry, we got your new password reset link right here: </h1> <br>' + reset_link
  # _email.html = render_template(template+'.html', **kwargs)
  mail.send(_email)
  if app.debug:
    app.logger.info('Reset link has been sent successfully to ' + email)
  return

@app.route('/api/register', methods=['POST'])
def register():
  """
      register() : Fetches documents from Firestore collection as JSON
      verif_email(email_link) : Void Function that send out a verification email to a newly registered user.
      
  """
  try:
    data = request.json
    if app.debug:
      app.logger.info(data)
    # Extract data from request
    display_name = data['user']['username']
    email = data['user']['email']
    # Create new user
    user = auth.create_user(display_name=display_name, email=email)
    if app.debug:
      app.logger.info('Sucessfully created new user: {0}'.format(user.uid))
    # User email verification
    email_link = auth.generate_email_verification_link(email, action_code_settings=None, app=None)
    verif_email(email, email_link)
    # Return created user information
    user = {
      'uid': user.uid,
      'email': user.email,
      'email_verified': user.email,
      'photo_url': user.photo_url
    }
    if app.debug:
      app.logger.info(user)
    return jsonify({'user': user})
  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/api/login', methods=['POST'])
def login():
  """
    login(): Return user login credentials and details
  """
  try:
    data = request.json
    if app.debug:
      app.logger.info(data)
    # Extract data from request
    email = data['user']['email']
    # Create new user
    user = auth.get_user_by_email(email, app=None)
    if app.debug:
      app.logger.info('Sucessfully signed in existing user: {0}'.format(user.email))
    # Return user information
    user = {
      'uid': user.uid,
      'email': user.email,
      'email_verified': user.email,
      'photo_url': user.photo_url
    }
    if app.debug:
      app.logger.info(user)
    return jsonify({'user': user})
  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/api/update', methods=['POST'])
def update_account():
  """
  """
  try:
    data = request.json
    if app.debug:
      app.logger.info(data)
    # Extract data from request
    uid = data['user']['uid']
    # Update user with new data
    user = auth.update_user(uid)
    if app.debug:
      app.logger.info('Sucessfully updated user information for existing user: {0}'.format(user.email))
    # Return user information
    user = {
      'uid': user.uid,
      'email': user.email,
      'email_verified': user.email,
      'photo_url': user.photo_url
    }
    if app.debug:
      app.logger.info(user)
    return jsonify({'user': user})
  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/reset_password', methods=['POST'])
def reset_password():
  try:
    data = request.json
    if app.debug:
      app.logger.info(data)
    # Extract email from data
    email = data['user']['email']
    # Send user password reset link:    
    auth.generate_password_reset_link(email, action_code_settings=None, app=None)
    return 'Password reset link sent'
  
  except Exception as e:
    return f"An Error Occured: {e}"

# =====
# LAUNCH-DATA ENDPOINTS
# ====
@app.route('/add_launch_data', methods=['POST'])
def add_launch():
  """
  """
  # data = requests.get('https://api.spacexdata.com/v4/launches')
  # response = json.dumps(data.json(), sort_keys = True, indent = 4, separators = (',', ': '))

  doc_ref = db.collection(u'launch').document(u'Falcom 9 | Merlin Mission')
  doc_ref.set({
    'id': '0',
    'company': 'SpaceX',
    'launch_date': '20/10/2020',
    'launch_time_unix': 1600510210,
    'live': True,
    'launch_site': 'Kennedy Space Center',
    'mission_title': 'Falcon Heavy Launch',
    'mission_desc': 'GPS-IIIA (Global Positioning System) is the first evolution stage of the third generation of the GPS satellites. It consists of the first ten (known as "tranche") of GPS III satellites.',
    'mission_tag': 'AlphaZero',
    'live_stream': 'https://www.youtube.com/embed/bnChQbxLkkI',
    'location': 'United States of America'
  })
  return 'Successful new data Addition'

@app.route('/launch_data', methods=['GET'])
def launch_data():
  """
    launch_data(): Returns the next 4 upcoming space launches as JSON
  """
  docs = db.collection(u'launch').stream()
  output = []
  for doc in docs:
    # output.append({
    #   'company': doc.get('company')})
    output.append(doc.to_dict())
    if app.debug:
      app.logger.info(f'{doc.id} => {doc.get("company")}')
  return jsonify({'result' : output})

@app.route('/launch_lib', methods=['GET'])
def launch_lib():
  data = requests.get('https://launchlibrary.net/1.4/launch/Falcon')
  output = []
  values = data.json()
  for launch in values['launches']:
    output.append({'result': launch})
  return jsonify({'result' : output})

# =====
# GALAXY-EXPLORER-DATA ENDPOINTS
# ====

@app.route('/galaxy_data', methods=['GET'])
def galaxy_data():
  """
  """
  return

# Different API's
# api.add_resource(HelloWorld, '/tasks')
# api.add_resource()
# api.add_resource()

if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=8080)