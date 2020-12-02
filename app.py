# -*- coding: utf-8 -*-
# !flask/bin/Python

import base64
import logging
import json
import requests
import time

import datetime
from datetime import timezone
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
# ---
# from flask_crontab import Crontab # ONLY WITH LINUX
# ---
from apscheduler.schedulers.background import BackgroundScheduler
import calendar

# ~~~~~~~~~~ Init APP ~~~~~~~~~~
app = Flask(__name__)
api = Api(app)
CORS(app)
# crontab = Crontab(app)

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

# =====
# NEWSLETTER SUB. ENDPOINTS
# ====

def news_sub_email(email):
  email_layout = Message("Welcome to ArkVision", sender='infospaceshadow@gmail.com', recipients=[email])
  email_layout.html = render_template('newsletter_welcome.html', email=email)
  mail.send(email_layout)
  return "Success"

@app.route('/news_sub', methods=['POST'])
def news_sub():
  """
  email(): Subscribes user to newsletter, returns Success / Error Message user
  """
  try:
    data = request.json
    email = data['email']
    if app.debug:
      app.logger.info(email)
    # Check if email is already registerd on the newsletter list, send conf. email if exists, and add to database,
    doc_ref = db.collection(u'newsletter_list').document(email)
    doc = doc_ref.get()
    if doc.exists:
      if app.debug:
        app.logger.info(f'Email already exists: {doc.to_dict()}')
      return jsonify({'errors': 'Email Already Registered!'})

    # Email not yet registered with us!
    else:
      if app.debug:
        app.logger.info(f'Email does not Exists: {doc.to_dict()}')
      doc_ref = db.collection(u'newsletter_list').document(email)
      doc_ref.set({
        u'timestamp': firestore.SERVER_TIMESTAMP
      })
      news_sub_email(email) # Send welcoming email
      return jsonify({'ok': 'Success!'})
 
  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/news_unsub/<string:email>')
def news_unsub(email):
  """
  news_unsub(): Unsubscribe user from the email list;
  """
  try:
    if app.debug:
      app.logger.info(email)
    # Remove email form the email-list
    doc_ref = db.collection(u'newsletter_list').document(email).delete()
    return render_template('news_unsub.html')
  except Exception as e:
    return f"An Error Occured: {e}"

# =====
# NOTIFICATION LAUNCH ENDPOINTS
# ====

def notifyConfirmEmail(email, launch_id):
  """
  confirmEmail(email, launch_id) : sends out email to user confirming the alert subscription to the launch,
  """
  email_layout = Message("Notification set! 🚀👩‍🚀", sender='infospaceshadow@gmail.com', recipients=[email])
  email_layout.html = render_template('notify_confirm.html', email=email, launch_id=launch_id)
  mail.send(email_layout)
  return "Success"

def notifyUsersAlertEmail(email, launch_id):
  with app.app_context():
    """
    notifyUsersAlertEmail(email, launch_id) : Sends out email to users registered for a launch to be notified,
    """
    email_layout = Message("T-15 Minutes 🚀👩‍🚀", sender='infospaceshadow@gmail.com', recipients=[email])
    email_layout.html = render_template('alert_notify_launch.html', email=email, launch_id=launch_id)
    mail.send(email_layout)
    return "Success"

def cronNotifChecker():
  """
  cronNotifChecker(): Checks periodically for uproaching launches to send out notification to registered users within 15 min. of the launch.
  """
  try:
    if app.debug:
      app.logger.info('Current server time: ' + time.strftime('%A %B, %d %Y %H:%M:%S'))
    # Get current local UTC time and compare it to the launch time;
    current_time = datetime.datetime.now(tz=timezone.utc)
    # Get all the launches and check for the launch times starting in 15 min;
    doc_ref = db.collection(u'launch')
    docs = doc_ref.where(u'notified', u'==', False).stream()
    for doc in docs:
      launch_date = doc.get("launch_date")
      time_dif = (launch_date - current_time)
      if app.debug:
        app.logger.info(time_dif.total_seconds())
      # If launch is wihtin 15 min. , trigger the launch alert for the notified users;
      if (time_dif.total_seconds() < 15 * 60):
        emails_list = doc.get('notify')
        for email in emails_list:
          if app.debug:
            app.logger.info('Sending email notifcation to -> ' + email + ' for launch: ' + doc.id)
            # logging.basicConfig()
            # logging.getLogger('apscheduler').setLevel(logging.DEBUG)
          notifyUsersAlertEmail(email, doc.id)
          # set the launch notification set to TRUE;
        doc_ref.document(doc.id).update({u'notified': True})
      
    return jsonify({'ok': 'Success!'})

  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/mobile_notif', methods=['POST'])
def mobile_notif():
  """
  """

  return

@app.route('/email_notif', methods=['POST'])
def email_notif():
  """
    email_notif(): Subscribes the user to an Email Notification update for a particular launch for 15min. before launch
  """
  try:
    data = request.json
    email = data['email']
    launch_id = data['launch_id']
    if app.debug:
      app.logger.info(data)
    # Get the target launch from the schedueled launch mission list, should return only a single launch mission with set ID, or none,
    doc_ref = db.collection(u'launch')
    query = doc_ref.where(u'id', u'==', launch_id).stream()
    for doc in query:
      if app.debug:
        app.logger.info(f'{doc.id} => {doc.get("company")}')
      # set notifcation for the user with set email, automically add a new region to the 'notify' array field
      doc_ref.document(doc.id).update({u'notify': firestore.ArrayUnion([email])})

    notifyConfirmEmail(email, launch_id) # confirmation notifcaiton set email:

    return jsonify({'ok': 'Success!'})

  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/email_notif_unsub/<string:email>/<string:launch_id>')
def email_notif_unsub(email, launch_id):
  """
  email_notif_unsub() : unsunbsribes the user target user from the launch alert notification,
  """
  try:
    if app.debug:
      app.logger.info('Email: ' + email + 'Launch ID: ' + launch_id)
    # Remove email form the email-list alert list for the launch
    doc_ref = db.collection(u'launch')
    query = doc_ref.where(u'id', u'==', launch_id).stream()
    for doc in query:
      if app.debug:
        app.logger.info(f'{doc.id} => {doc.get("company")}')
      doc_ref.document(doc.id).update({u'notify': firestore.ArrayRemove([email])})
    return render_template('alert_unsub_page.html')

  except Exception as e:
    return f"An Error Occured: {e}"

# Initialize the Notification Checker Scheduler for Viewing Space launch times - [Working]
# sched = BackgroundScheduler(daemon=True)
# sched.add_job(cronNotifChecker, 'interval', minutes=1,  id='cronNotifChecker', replace_existing=True)
# sched.start()

# =====
# CHAT ENDPOINTS
# ====

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
  welcome_email = Message("Welcome to ArkVision! 🚀🌌", sender='infospaceshadow@gmail.com', recipients=[email])
  welcome_email.html = render_template('verify_email.html', email_link=email_link)
  mail.send(welcome_email)
  if app.debug:
    app.logger.info('Email Send successfully to ' + email)
  return

def reset_password(email, pass_reset_link):
  _email = Message('Password Reset Link', sender='infospaceshadow@gmail.com', recipients=[email])
  _email.html = render_template('user_reset_pass.html', pass_reset_link=pass_reset_link)
  mail.send(_email)
  # == TEST ==
  if app.debug:
    app.logger.info('Reset link has been sent successfully to ' + email)
  return

@app.route('/api/register', methods=['POST'])     # Working & Setup
def register():
  """
  register() : Fetches documents from Firestore collection as JSON
  verif_email(email_link) : Void Function that send out a verification email to a newly registered user.
  """
  try:
    data = request.json
    # == TEST ==
    if app.debug:
      app.logger.info(data)
    # Extract data from request
    username = data['user']['username']
    email = data['user']['email']
    password = data['user']['password']
    # Create new user
    user = auth.create_user(display_name=username, email=email, password=password)
    # Populate the DB with more data;
    db.collection(u'users').document(user.uid).set({u'email': email, u'username': username, u'favourite_news': []})
    # == TEST ==
    if app.debug:
      app.logger.info('Sucessfully created new user: {0}'.format(user.uid))
    # User email verification
    email_link = auth.generate_email_verification_link(email, action_code_settings=None, app=None)
    verif_email(email, email_link)
    # Return created user information
    user = {
      'uid': user.uid,
      'username': user.display_name,            # originally display_name
      'email': user.email,
      'email_verified': user.email_verified,
      'photo_url': user.photo_url
    }
    # == TEST ==
    if app.debug:
      app.logger.info(user)
    return jsonify({'user': user})
    
  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/api/login', methods=['POST'])        # Working & Setup
def login():
  """
  login(): Return user login credentials and details
    creates a separate firestore location for the users additional set of data
  """
  try:
    data = request.json
    # == TEST ==
    if app.debug:
      app.logger.info(data)
    # Extract data from request
    email = data['user']['email']
    password = data['user']['password']
    # Create new user
    user = auth.get_user_by_email(email, app=None)
    # == TEST ==
    if app.debug:
      app.logger.info('Sucessfully signed in existing user: {0}'.format(user.email))
    # Return user information
    user = {
      'uid': user.uid,
      'username': user.display_name,            # originally display_name
      'email': user.email,
      'email_verified': user.email_verified,
      'photo_url': user.photo_url
    }
    # == TEST ==
    if app.debug:
      app.logger.info(user)

    return jsonify({'user': user})

  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/api/update', methods=['POST'])       # Working & Setup
def update_account():
  """
  update_account() : updates target user account with news information from settings page;
  parameters - { email, password, display_name }
  """
  try:
    # declaring user;
    req_head = request.headers['Authorization']
    data = request.json
    user = data['user']
    # == TEST ==
    if app.debug:
      app.logger.info(data)
      app.logger.info(req_head)
    # Extract data from request
    uid = req_head
    email = data['user']['email']
    password = data['user']['password']
    display_name = data['user']['username']
    # Deal with the password reset for the user, generating a new password reset link:
    if password != '':
      # == TEST ==
      if app.debug:
        app.logger.info("Updating with password")
      user = auth.update_user(uid, email=email, password=password, display_name=display_name)
      pass_reset_link = auth.generate_password_reset_link(email, action_code_settings=None, app=None)
      reset_password(email, pass_reset_link)
    else:
      # == TEST ==
      if app.debug:
        app.logger.info("Updating without password")
      # Update user with new data
      user = auth.update_user(uid, email=email, display_name=display_name)
    # == TEST ==
    if app.debug:
      app.logger.info('Sucessfully updated user information for existing user: {0}'.format(user.email))
    # Return user information
    user = {
      'uid': user.uid,
      'username': user.display_name,            # originally display_name
      'email': user.email,
      'email_verified': user.email_verified,
      'photo_url': user.photo_url
    }
    # == TEST ==
    if app.debug:
      app.logger.info(user)

    return jsonify({'user': user})

  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/api/get_news_fav', methods=['POST'])  # Working & Setup
def get_news_fav():
  """
  news_fav() : Adds news to users favourite news to a list on the DB,
  [POST] return - error message
  """
  try:
    data = request.json
    uid = data['uid']
    # == TEST ==
    if app.debug:
      app.logger.info(uid)
    # Get user new_letters ref. from DB
    doc_ref = db.collection(u'users').document(uid)
    doc = doc_ref.get()
    if doc.exists:
      print(f'Document data: {doc.to_dict()}')
      favourite_list = doc.get("favourite_news")
      return jsonify({u'fav_news': 'favourite_list'})
    else:
      print(u'No such document!')
      return jsonify({'ok': 'Error!'})

  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/api/set_news_fav', methods=['POST'])  # Working & Setup
def set_news_fav():
  """
  news_fav() : Adds news to users favourite news to a list on the DB,
  [POST] return - error message
  """
  try:
    data = request.json
    uid = data['uid']
    news_id = data['news_id']
    # == TEST ==
    if app.debug:
      app.logger.info(uid)
    # Get user new_letters ref. from DB
    doc_ref = db.collection(u'users').document(uid)
    favourite_list = doc_ref.get(u'favourite_news')
    doc = doc_ref.get()
    if doc.exists:
      print(f'Document data: {doc.to_dict()}')
      doc_ref.update({u'favourite_news': firestore.ArrayUnion([news_id])})
      return jsonify({'ok': 'Success!'})

    else:
        print(u'No such document!')
        return jsonify({'ok': 'Error!'})

  except Exception as e:
    return f"An Error Occured: {e}"

@app.route('/get_user', methods=['GET'])
def get_user():
  """
  get_user() : get the entire user data and profile information, for an already auth. user
  return - JSON Response for the user data,
  """
  try:
    data = request.json
    email = data['email']
    # Check if email is already registerd on the newsletter list, send conf. email if exists, and add to database,
    doc_ref = db.collection(u'users').document(email)
    user_data = doc_ref.get('favourite_news')
    user_profile = []
    user_profile = [{ }]
    return jsonify({'user_profile': favourite_list})

  except Exception as e:
    return f"An Error Occured: {e}"

# @app.route('/reset_password', methods=['POST'])
  # def reset_password():
  #   try:
  #     data = request.json
  #     if app.debug:
  #       app.logger.info(data)
  #     # Extract email from data
  #     email = data['user']['email']
  #     # Send user password reset link:    
  #     auth.generate_password_reset_link(email, action_code_settings=None, app=None)
  #     return 'Password reset link sent'
  
  except Exception as e:
    return f"An Error Occured: {e}"

# =====
# LAUNCH-DATA ENDPOINTS
# ====

@app.route('/add_launch_data', methods=['POST'])   # Working & Setup
def add_launch():
  """
  add_launch() : Add launch data to the DB in .json format
  """

  # data = requests.get('https://api.spacexdata.com/v4/launches')
  # response = json.dumps(data.json(), sort_keys = True, indent = 4, separators = (',', ': '))

  # Load Target File:
  data = json.load(open('api_schema/schema_launch_data.json'))

  # Load Target Data:
  for item in data:
    doc_ref = db.collection(u'launch').document(item['mission_title'])
    doc_ref.set(item)
  return 'Successful new data Addition'

@app.route('/launch_data', methods=['GET'])        # Working & Setup
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
  """
  launch_lib() : [GET] and streamline the launch_lib/api for custom use,
  """
  _data = requests.get('https://ll.thespacedevs.com/2.0.0/launch/upcoming/')
  output = []
  data = _data.json()
  # customize the target API to our needs:
  for launch in data['results']:

    unix_timestamp = datetime.datetime.strptime(launch['net'], '%Y-%m-%dT%H:%M:%SZ').timestamp()

    id = ''
    if launch['id'] is None: id = 'nan'
    else: id = launch['id'] 
    
    company = ''
    if launch['launch_service_provider']['name'] is None: company = 'nan'
    else: company = launch['launch_service_provider']['name']

    launch_site = ''
    location = ''
    if launch['pad'] is None: launch_site = 'nan'
    else: 
      launch_site = launch['pad']['name']
      location = launch['pad']['location']['country_code']

    mission_title = ''
    mission_tag = ''
    mission_desc = ''
    if launch['mission'] is None: mission_title = 'nan' 
    else: 
      mission_title = launch['mission']['name']
      mission_tag = launch['mission']['name']
      mission_desc = launch['mission']['description']

    launch_date = ''
    if launch['net'] is None: launch_date = 'nan'
    else: launch_date = launch['net']

    output.append({
      'id': id,
      'company': company,
      'mission_title' : mission_title,
      'launch_site': launch_site,
      'launch_time_unix': unix_timestamp,
      'launch_date': launch_date,
      'live': False,
      'mission_desc': mission_desc,
      'mission_tag': mission_tag,
      "live_stream": "https://www.youtube.com/embed/bnChQbxLkkI",
      "location": location,
      "notified": False,
      "notify": []
    })

    # Save to a file
    # Serializing json  
    json_object = json.dumps(output, indent = 4) 
      
    # Writing to sample.json 
    with open("api_schema/schema_launch_data.json", "w") as outfile: 
      outfile.write(json_object) 
    
  return jsonify({'result' : output})

# @app.route('/')

# =====
# GALAXY-EXPLORER-DATA ENDPOINTS
# ====

@app.route('/galaxy_data', methods=['GET'])
def galaxy_data():
  """
  """
  return

# ====
# ADMIN CONTROL
# ====

@app.route('/delete_user/<string:user_uid>')
def delete_user(user_uid):
  """
  delete_user() : Deletes a target user from the Database;
  """
  auth.delete_user(user_uid, app=None)
  return {'ok': 'User Successfully deleted'}

# Different API's
# api.add_resource(HelloWorld, '/tasks')
# api.add_resource()
# api.add_resource()

if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=8080)
