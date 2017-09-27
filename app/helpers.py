# -*- coding: utf-8 -*-
import base64
import json

from flask import request, make_response

from six.moves.urllib.parse import urlparse, urlunparse

from .structures import CaseInsensitiveDict

ASCII_ART = '''
    -=[ teapot ]=-

       _...._
     .'  _ _ `.
    | ."` ^ `". _,
    \_;`"---"`|//
      |       ;/
      \_     _/
        `\"\"\"`
'''

REDIRECT_LOCATION = '/redirect/1'

ACCEPTED_MEDIA_TYPES = [
    'image/webp',
    'image/svg+xml',
    'image/jpeg',
    'image/png',
    'image/*'
]

ENV_HEADERS = (
    'X-Varnish',
    'X-Request-Start',
    'X-Heroku-Queue-Depth',
    'X-Real-Ip',
    'X-Forwarded-Proto',
    'X-Forwarded-Protocol',
    'X-Forwarded-Ssl',
    'X-Heroku-Queue-Wait-Time',
    'X-Forwarded-For',
    'X-Heroku-Dynos-In-Use',
    'X-Forwarded-For',
    'X-Forwarded-Protocol',
    'X-Forwarded-Port',
    'X-Request-Id',
    'Via',
    'Total-Route-Time',
    'Connect-Time'
)

def json_safe(string, content_type='application/octet-stream'):
    """Returns JSON-safe version of `string`.

    If `string` is a Unicode string or a valid UTF-8, it is returned unmodified,
    as it can safely be encoded to JSON string.

    If `string` contains raw/binary data, it is Base64-encoded, formatted and
    returned according to "data" URL scheme (RFC2397). Since JSON is not
    suitable for binary data, some additional encoding was necessary; "data"
    URL scheme was chosen for its simplicity.
    """
    try:
        string = string.decode('utf-8')
        json.dumps(string)
        return string
    except (ValueError, TypeError):
        return b''.join([
            b'data:',
            content_type.encode('utf-8'),
            b';base64,',
            base64.b64encode(string)
        ]).decode('utf-8')

def semiflatten(multi):
    '''将multi转化为普通的字典，如果某个键对应的值多于一个，则这个键将对应一组值的列表，否则对应一个值'''
    if multi:
        result = multi.to_dict(flat=False)
        for k, v in result.items():
            if len(v) == 1:
                result[k] = v[0]
        return result
    else:
        return multi

def get_url(request):
    """
    Since we might be hosted behind a proxy, we need to check the
    X-Forwarded-Proto, X-Forwarded-Protocol, or X-Forwarded-SSL headers
    to find out what protocol was used to access us.
    """
    protocol = request.headers.get('X-Forwarded-Proto') or request.headers.get('X-Forwarded-Protocol')
    if protocol is None and request.headers.get('X-Forwarded-Ssl') == 'on':
        protocol = 'https'
    if protocol is None:
        return request.url
    url = list(urlparse(request.url))
    url[0] = protocol
    return urlunparse(url)


def get_headers(hide_env=True):
    '''通过请求上下文返回headers'''
    """Returns headers dict from request context."""

    headers = dict(request.headers.items())

    if hide_env and ('show_env' not in request.args):
        for key in ENV_HEADERS:
            try:
                del headers[key]
            except KeyError:
                pass

    return CaseInsensitiveDict(headers.items())

def get_files():
    '''通过请求上下文返回文件字典'''
    """Returns files dict from request context."""

    files = dict()

    for k, v in request.files.items():
        content_type = request.files[k].content_type or 'application/octet-stream'
        val = json_safe(v.read(), content_type)
        if files.get(k):
            if not isinstance(files[k], list):
                files[k] = [files[k]]
            files[k].append(val)
        else:
            files[k] = val

    return files

def get_dict(*keys, **extras):
    '''根据给定的keys返回请求的字典'''

    _keys = ('url', 'args', 'form', 'data', 'origin', 'headers', 'files', 'json', 'method')

    # 以一种非常炫酷的方式验证参数 keys 在 _keys 中
    assert all(map(_keys.__contains__, keys))
    data = request.data
    form = semiflatten(request.form)

    try:
        _json = json.loads(data.decode('utf-8'))
    except (ValueError, TypeError):
        _json = None

    d = dict(
        url=get_url(request),
        args=semiflatten(request.args),
        form=form,
        data=json_safe(data),
        origin=request.headers.get('X-Forwarded-For', request.remote_addr),
        headers=get_headers(),
        files=get_files(),
        json=_json,
        method=request.method,
    )

    out_d = dict()

    for key in keys:
        out_d[key] = d.get(key)

    out_d.update(extras)

    return out_d


def status_code(code):
    '''根据给定的状态码返回响应对象'''

    redirect = dict(headers=dict(location=REDIRECT_LOCATION))

    code_map = {
        301: redirect,
        302: redirect,
        303: redirect,
        304: dict(data=''),
        305: redirect,
        307: redirect,
        401: dict(headers={'WWW-Authenticate': 'Basic realm="Fake Realm"'}),
        402: dict(
            data='Fuck you, pay me!',
            headers={
                'x-more-info': 'http://vimeo.com/22053820'
            }
        ),
        406: dict(data=json.dumps({
                'message': 'Client did not request a supported media type.',
                'accept': ACCEPTED_MEDIA_TYPES
            }),
            headers={
                'Content-Type': 'application/json'
            }),
        407: dict(headers={'Proxy-Authenticate': 'Basic realm="Fake Realm"'}),
        418: dict(  # I'm a teapot!
            data=ASCII_ART,
            headers={
                'x-more-info': 'http://tools.ietf.org/html/rfc2324'
            }
        ),

    }

    r = make_response()
    r.status_code = code

    if code in code_map:

        m = code_map[code]

        if 'data' in m:
            r.data = m['data']
        if 'headers' in m:
            r.headers = m['headers']

    return r

def secure_cookie():
    '''如果 Cookie 应该具有安全属性 则返回 True'''
    return request.environ['wsgi.url_scheme'] == 'https'