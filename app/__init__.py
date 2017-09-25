# -*- coding: utf-8 -*-
from flask import Flask

def create_app():
    app = Flask(__name__)

    from core import core
    app.register_blueprint(core)

    return app