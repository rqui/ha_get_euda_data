import unittest
from types import SimpleNamespace
from test_eudaconnection_merge import _load_package

class Response:
    def __init__(self, url, text='', status=200, headers=None):
        self.url, self._text, self.status, self.headers = url, text, status, headers or {}
    async def text(self): return self._text

class LoginTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_form_posts_to_identity_and_resolves_redirect(self):
        m = _load_package()
        class Session:
            async def post(self, **kw):
                self.kw=kw
                return Response(kw['url'], status=302, headers={'Location':'/authorize/resume?state=synthetic'})
        session=Session()
        conn=m.EUDAConnection(session=session, username='user', password='password')
        page=Response('https://identity.vwgroup.io/u/login?state=synthetic', '<form method="post"><input type="hidden" name="state" value="synthetic"><input name="username"><input name="password"><button type="submit" name="action" value="default"></button></form>')
        result=await conn._signin_universal(page, 'https://identity.vwgroup.io')
        self.assertEqual(result, 'https://identity.vwgroup.io/authorize/resume?state=synthetic')
        self.assertEqual(session.kw['data'], {'state':'synthetic', 'username':'user', 'password':'password', 'action':'default'})
        self.assertFalse(session.kw['allow_redirects'])
    async def test_rejects_cross_origin_action(self):
        m=_load_package(); conn=m.EUDAConnection(session=None, username='user', password='password')
        page=Response('https://identity.vwgroup.io/u/login', '<form method="post" action="https://other.invalid/"><input name="username"><input name="password"></form>')
        with self.assertRaises(m.PyCupraLoginFailedException): await conn._signin_universal(page, 'https://identity.vwgroup.io')
