import requests, time

BASE = 'http://127.0.0.1:8003'

email = f'integ_test_{int(time.time())}@example.com'
password = 'TestPass123!'

print('Registering user', email)
res = requests.post(f'{BASE}/register', json={'full_name':'Integration Test','email':email,'password':password}, timeout=20)
print('register:', res.status_code, res.text)
if res.status_code not in (200,201):
    raise SystemExit('Register failed')

print('Logging in')
res = requests.post(f'{BASE}/login', json={'email':email,'password':password}, timeout=20)
print('login:', res.status_code, res.text)
if res.status_code not in (200,201):
    raise SystemExit('Login failed')

data = res.json()
token = data.get('access_token')
if not token:
    raise SystemExit('No token returned')

headers = {'Authorization': f'Bearer {token}'}

print('Calling /me')
me_res = requests.get(f'{BASE}/me', headers=headers, timeout=20)
print('/me', me_res.status_code, me_res.text)

print('Calling GET /hcps (protected)')
hcps_res = requests.get(f'{BASE}/hcps', headers=headers, timeout=20)
print('/hcps', hcps_res.status_code, hcps_res.text)

print('Integration test completed')
