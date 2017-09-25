# -*- coding: utf-8 -*-
import uuid

from flask import Blueprint, jsonify, make_response, render_template, request

from config import *
from .helpers import get_dict, get_headers

core = Blueprint('core', __name__)

@core.route('/')
def view_main_page():
    '''生成主页面.'''
    return render_template('index.html')

@core.route('/robots.txt')
def view_robots_page():
    '''显示robots'''
    response = make_response()
    response.data = ROBOT_TXT
    response.content_type = "text/plain"
    return response

@core.route('/deny')
def view_deny_page():
    '''不应被请求的页面'''
    response = make_response()
    response.data = ANGRY_ASCII
    response.content_type = "text/plain"
    return response

@core.route('/html')
def view_html_page():
    """HTML 页面"""

    return render_template('moby.html')

@core.route('/ip')
def view_origin():
    '''返回请求IP'''

    return jsonify(origin=request.headers.get('X-Forwarded-For', request.remote_addr))

@core.route('/uuid')
def view_uuid():
    '''生成并返回uuid'''

    return jsonify(uuid=str(uuid.uuid4()))

@core.route('/headers')
def view_headers():
    '''返回HTTP请求的headers'''

    return jsonify(get_dict('headers'))

@core.route('/user-agent')
def view_user_agent():
    '''返回 User-Agent'''

    headers = get_headers()

    return jsonify({'user-agent': headers['user-agent']})

@core.route('/get', methods=('GET',))
def view_get():
    """返回 GET 数据"""

    return jsonify(get_dict('url', 'args', 'headers', 'origin'))

@core.route('/post', methods=('POST',))
def view_post():
    '''返回 POST 数据'''

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json'))

@core.route('/put', methods=('PUT',))
def view_put():
    '''返回 PUT 数据'''

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json'))


@core.route('/patch', methods=('PATCH',))
def view_patch():
    '''返回 PATCH 数据'''

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json'))


@core.route('/delete', methods=('DELETE',))
def view_delete():
    '''返回 DELETE 数据'''

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json'))

@core.route('/anything', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'TRACE'])
@core.route('/anything/<path:anything>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'TRACE'])
def view_anything(anything=None):
    '''返回请求数据'''

    return jsonify(get_dict('url', 'args', 'headers', 'origin', 'method', 'form', 'data', 'files', 'json'))
