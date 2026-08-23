import requests, time

BASE='http://127.0.0.1:8003'
# Use a temp test user for the flow
email=f'phase3_test_{int(time.time())}@example.com'
password='Phase3Pass!'
print('Registering user', email)
r=requests.post(f'{BASE}/register', json={'full_name':'Phase3 Test','email':email,'password':password}, timeout=20)
print('register', r.status_code, r.text)
if r.status_code not in (200,201):
    raise SystemExit('register failed')

print('Logging in')
res=requests.post(f'{BASE}/login', json={'email':email,'password':password}, timeout=20)
print('login', res.status_code, res.text)
if res.status_code not in (200,201):
    raise SystemExit('login failed')

token=res.json().get('access_token')
headers={'Authorization':f'Bearer {token}'}

# Step 3: GET /hcps with JWT
print('GET /hcps')
hcps_res=requests.get(f'{BASE}/hcps', headers=headers, timeout=20)
print('/hcps', hcps_res.status_code, hcps_res.text)
existing_hcps=hcps_res.json()
existing_count=len(existing_hcps)
print('existing_count=', existing_count)

# Step 4: Create temporary HCP
new_hcp = {
    'doctor_name':'Temp Doctor X',
    'specialization':'General',
    'hospital':'Test Hospital',
    'city':'Test City',
    'phone':f'999{int(time.time())%1000000}',
    'email':f'tempdoc{int(time.time())}@example.com'
}
print('Creating HCP')
create_res=requests.post(f'{BASE}/hcps', json=new_hcp, headers=headers, timeout=20)
print('create_hcp', create_res.status_code, create_res.text)
if create_res.status_code not in (200,201):
    raise SystemExit('create_hcp failed')
created_id=create_res.json().get('doctor_id')
print('created_id=', created_id)

# Step 5: Retrieve the temporary HCP
get_res=requests.get(f'{BASE}/hcps/{created_id}', headers=headers, timeout=20)
print('get_hcp', get_res.status_code, get_res.text)

# Step 6: Update the temporary HCP
update_payload = new_hcp.copy()
update_payload['city']='Updated City'
put_res=requests.put(f'{BASE}/hcps/{created_id}', json=update_payload, headers=headers, timeout=20)
print('update_hcp', put_res.status_code, put_res.text)

# Step 7: Create temporary interaction linked to that HCP
from datetime import datetime, timedelta
follow_up = (datetime.utcnow()+timedelta(days=7)).isoformat()
interaction_payload = {
    'user_id': res.json().get('id', None) or r.json().get('user_id'),
    'hcp_id': created_id,
    'meeting_notes':'Test meeting notes',
    'products_discussed':'ProductA',
    'follow_up_date': follow_up
}
print('Creating interaction', interaction_payload)
int_res = requests.post(f'{BASE}/interactions', json=interaction_payload, headers=headers, timeout=20)
print('create_interaction', int_res.status_code, int_res.text)
if int_res.status_code not in (200,201):
    print('interaction creation failed (as expected if validation failed)')

# Step 8: Retrieve/list interactions
list_res = requests.get(f'{BASE}/interactions', headers=headers, timeout=20)
print('list_interactions', list_res.status_code, list_res.text)

# Step 9: Test invalid HCP reference
bad_payload = interaction_payload.copy(); bad_payload['hcp_id']=999999999
bad_res = requests.post(f'{BASE}/interactions', json=bad_payload, headers=headers, timeout=20)
print('bad_interaction', bad_res.status_code, bad_res.text)

# Step 10: Test unauthenticated CRM request
unauth = requests.get(f'{BASE}/hcps', timeout=20)
print('unauth /hcps', unauth.status_code, unauth.text)

# Step 11: Delete temporary HCP
del_res = requests.delete(f'{BASE}/hcps/{created_id}', headers=headers, timeout=20)
print('delete_hcp', del_res.status_code, del_res.text)

# Step 12: Confirm existing HCPs remain
final_hcps = requests.get(f'{BASE}/hcps', headers=headers, timeout=20).json()
print('final count', len(final_hcps), 'existing_count', existing_count)

print('Phase 3 test completed')
