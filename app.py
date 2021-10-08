import os
import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt

import config.settings as settings


app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URI
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(weeks=2)
app.secret_key = 'settings.SECRET_KEY'

migrate = Migrate(compare_type=True)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

app_ids = {
    'investor': '06fb7ef6-8f23-4d66-a8c2-a1025fb5f7ad'
}

@jwt.expired_token_loader
def my_expired_token_callback(expired_token):
    pass

db = SQLAlchemy(app)
CORS(app, resources={r'/*': {'origins': '*'}})



import views.admin
import views.main
import views.product
import views.investor

migrate.init_app(app, db)
