# -*- coding: utf-8 -*-
import json
import time
import uuid
import base64

from flask import (Blueprint, Response, jsonify, make_response, redirect,
                   render_template, request, url_for)
from werkzeug.datastructures import MultiDict, WWWAuthenticate

from config import *

from .helpers import get_dict, get_headers, secure_cookie, status_code
from .structures import CaseInsensitiveDict

ENV_COOKIES = (
    '_gauges_unique',
    '_gauges_unique_year',
    '_gauges_unique_month',
    '_gauges_unique_day',
    '_gauges_unique_hour',
    '__utmz',
    '__utma',
    '__utmb'
)

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

@core.route('/redirect/<int:n>')
def redirect_n_times(n):
    '''302 重定向 n 次'''
    assert n > 0

    absolute = request.args.get('absolute', 'false').lower() == 'true'

    if n == 1:
        return redirect(url_for('core.view_get', _external=absolute))

    if absolute:
        return _redirect('absolute', n, True)
    else:
        return _redirect('relative', n, False)

def _redirect(kind, n, external):
    return redirect(url_for('core.{0}_redirect_n_times'.format(kind), n=n - 1, _external=external))

@core.route('/relative-redirect/<int:n>')
def relative_redirect_n_times(n):
    '''302 重定向 n 次'''

    assert n > 0

    response = make_response('')
    response.status_code = 302

    if n == 1:
        response.headers['Location'] = url_for('core.view_get')
        return response

    response.headers['Location'] = url_for('core.relative_redirect_n_times', n=n - 1)
    return response


@core.route('/absolute-redirect/<int:n>')
def absolute_redirect_n_times(n):
    '''302 重定向 n 次'''

    assert n > 0

    if n == 1:
        return redirect(url_for('core.view_get', _external=True))

    return _redirect('absolute', n, True)

@core.route('/redirect-to', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'TRACE'])
def redirect_to():
    '''302/3XX 重定向至给定的 URL'''

    args = CaseInsensitiveDict(request.args.items())

    # We need to build the response manually and convert to UTF-8 to prevent
    # werkzeug from "fixing" the URL. This endpoint should set the Location
    # header to the exact string supplied.
    response = make_response('')
    response.status_code = 302
    if 'status_code' in args:
        status_code = int(args['status_code'])
        if status_code >= 300 and status_code < 400:
            response.status_code = status_code
    response.headers['Location'] = args['url'].encode('utf-8')

    return response


@core.route('/stream/<int:n>')
def stream_n_messages(n):
    '''n 行 JSON 流信息'''
    response = get_dict('url', 'args', 'headers', 'origin')
    n = min(n, 100)

    def generate_stream():
        for i in range(n):
            response['id'] = i
            yield json.dumps(response) + '\n'

    return Response(generate_stream(), headers={
        "Content-Type": "application/json",
        })

@core.route('/status/<codes>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'TRACE'])
def view_status_code(codes):
    '''返回指定 Code 或以逗号分割看的随机 Code 状态的页面'''

    if ',' not in codes:
        try:
            code = int(codes)
        except ValueError:
            return Response('Invalid status code', status=400)
        return status_code(code)

    choices = []
    for choice in codes.split(','):
        if ':' not in choice:
            code = choice
            weight = 1
        else:
            code, weight = choice.split(':')

        try:
            choices.append((int(code), float(weight)))
        except ValueError:
            return Response('Invalid status code', status=400)

    code = weighted_choice(choices)

    return status_code(code)

@core.route('/response-headers', methods=['GET', 'POST'])
def response_headers():
    '''从查询字符串中返回一组响应头'''
    headers = MultiDict(request.args.items(multi=True))
    response = jsonify(list(headers.lists()))

    while True:
        original_data = response.data
        d = {}
        for key in response.headers.keys():
            value = response.headers.get_all(key)
            if len(value) == 1:
                value = value[0]
            d[key] = value
        response = jsonify(d)
        for key, value in headers.items(multi=True):
            response.headers.add(key, value)
        response_has_changed = response.data != original_data
        if not response_has_changed:
            break
    return response


@core.route('/cookies')
def view_cookies(hide_env=True):
    '''返回 cookie 数据'''

    cookies = dict(request.cookies.items())

    if hide_env and ('show_env' not in request.args):
        for key in ENV_COOKIES:
            try:
                del cookies[key]
            except KeyError:
                pass

    return jsonify(cookies=cookies)

@core.route('/cookies/set')
def set_cookies():
    '''设置由查询字符串提供的cookie，并重定向到cookie列表'''

    cookies = dict(request.args.items())
    r = make_response(redirect(url_for('core.view_cookies')))
    for key, value in cookies.items():
        r.set_cookie(key=key, value=value, secure=secure_cookie())

    return r

@core.route('/cookies/delete')
def delete_cookies():
    '''删除由查询字符串提供的cookie，并重定向到cookie列表'''

    cookies = dict(request.args.items())
    r = make_response(redirect(url_for('core.view_cookies')))
    for key, value in cookies.items():
        r.delete_cookie(key=key)

    return r

@core.route('/delay/<delay>')
def delay_response(delay):
    '''返回延迟响应'''
    delay = min(float(delay), 10)

    time.sleep(delay)

    return jsonify(get_dict(
        'url', 'args', 'form', 'data', 'origin', 'headers', 'files'))

@core.route('/base64-encode/<value>')
def encode_base64(value):
    '''加密 base64 的数据'''
    encoded = value.encode('utf-8')
    return base64.urlsafe_b64encode(encoded).decode('utf-8')

@core.route('/base64-decode/<value>')
def decode_base64(value):
    '''解码 base64 的数据'''
    encoded = value.encode('utf-8')
    return base64.urlsafe_b64decode(encoded).decode('utf-8')
