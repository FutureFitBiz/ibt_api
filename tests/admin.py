import unittest
import json

from tests import TestBase
from app import bcrypt


#class TestAdminBasics(unittest.TestCase):
class TestAdminBasics(TestBase):
    def get_auth_key(self):
        test_password = '123456'
        test_login = 'tester@futurefitbusiness.org'
        response = self.test_client_app.post('/login',
                    data=json.dumps({'email': test_login, 'password': test_password, 'app': 'admin'}),
                    content_type='application/json',)

        data = json.loads(response.data)
        self.assertIsNotNone(data.get('access_token'))
        access_token = data.get('access_token')
        return access_token

    def get_auth_header(self, access_token):
        return {'Authorization': 'Bearer {}'.format(access_token)}

    def test_login(self):
        #Test bad login
        response = self.test_client_app.post('/login',
                    data=json.dumps({'email': 'pumpkin', 'password': 'pizza', 'app': 'admin'}),
                    content_type='application/json')

        data = json.loads(response.data)
        self.assertTrue(data['message'] == 'Invalid username/password')

        #test no auth key
        response = self.test_client_app.get('/user/profile')
        data = json.loads(response.data)
        self.assertTrue(data['msg'] == 'Missing Authorization Header')

        #test auth key
        access_token = self.get_auth_key()
        headers = self.get_auth_header(access_token)

        response = self.test_client_app.get('/user/profile', headers=headers)
        data = json.loads(response.data)['data']

        self.assertTrue(data['first'] == 'tester')

    def test_user_crud(self):
        access_token = self.get_auth_key()
        headers = self.get_auth_header(access_token)

        #get first company
        response = self.test_client_app.get('/admin/company', headers=headers)
        company_data = json.loads(response.data)['data']
        company_id = company_data[0]['id']

        user = {'email': 'crud@test.com',
                'first': 'crud',
                'last': 'tester',
                'password': bcrypt.generate_password_hash('stupidbunny').decode('utf - 8'),
                'admin': True,
                'company_id': company_id
                }

        #optional
        response = self.test_client_app.post('/admin/user',
                                    data=json.dumps({'data': user}),
                                    content_type='application/json',
                                    headers=headers)

        data = json.loads(response.data)
        self.assertTrue(data['status'] == 'success')

        #now get the get_users
        response = self.test_client_app.get('/admin/user',
                                    headers=headers)

        data = json.loads(response.data)['data']
        found_user = None
        for found in data:
            if found['email'] == user['email']:
                found_user = found
                break

        self.assertIsNotNone(found_user)
        self.assertTrue(found_user['first'] == user['first'])
        self.assertTrue(found_user['last'] == user['last'])

        #update existing
        user['first'] = 'pumpkin'
        user['last'] = 'patch'
        user['id'] = found_user['id']

        response = self.test_client_app.post('/admin/user',
                                    data=json.dumps({'data': user}),
                                    content_type='application/json',
                                    headers=headers)

        data = json.loads(response.data)
        self.assertTrue(data['status'] == 'success')

        #get user and check updated
        response = self.test_client_app.get('/admin/user/%s'%(user['id']),
                                    headers=headers)

        data = json.loads(response.data)
        self.assertTrue(data['first'] == user['first'])
        self.assertTrue(data['last'] == user['last'])
        self.assertTrue(data['id'] == user['id'])

        #delete user
        response = self.test_client_app.get('/admin/user/delete/%s'%(user['id']),
                                    headers=headers)

        data = json.loads(response.data)
        self.assertTrue(data['status'] == 'success')

        #ensure deleted
        response = self.test_client_app.get('/admin/user',
                                    headers=headers)

        data = json.loads(response.data)['data']
        found_user = None
        for found in data:
            if found['id'] == user['id']:
                found_user = found
                break

        self.assertIsNone(found_user)

if __name__ == '__main__':
    unittest.main()
