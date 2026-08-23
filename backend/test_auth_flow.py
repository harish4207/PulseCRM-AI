import requests, time
base='http://127.0.0.1:8003'
email=f'testuser_{int(time.time())}@example.com'
print('Registering', email)
r=requests.post(base+'/register', json={'full_name':'API Test','email':email,'password':'testpass'}, timeout=20)
print('register status', r.status_code, r.text)
if r.status_code in (200,201):
    print('Now logging in')
    lr=requests.post(base+'/login', json={'email':email,'password':'testpass'}, timeout=20)
    print('login status', lr.status_code, lr.text)
else:
    print('register did not succeed')
