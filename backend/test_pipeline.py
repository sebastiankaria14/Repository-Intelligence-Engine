import urllib.request
import urllib.error
import json
import time

# Create repository
try:
    req = urllib.request.Request(
        'http://localhost:8001/api/repositories',
        data=json.dumps({'github_url': 'https://github.com/octocat/Hello-World'}).encode(),
        headers={'Content-Type': 'application/json', 'X-API-Key': 'rie_dev_api_key'}
    )
    resp = urllib.request.urlopen(req)
    repo = json.loads(resp.read().decode())
    print('Created repo:', repo['id'])
    repo_id = repo['id']
except Exception as e:
    print('Create failed:', e)
    exit(1)

# Check status with longer waits
for i in range(10):
    try:
        req = urllib.request.Request(f'http://localhost:8001/api/repositories/{repo_id}/status')
        resp = urllib.request.urlopen(req)
        status = json.loads(resp.read().decode())
        print(f'Check {i+1}: {status.get("status")} - {status.get("current_phase")} - {status.get("progress")}%')
        if status.get('status') in ('completed', 'failed'):
            print('Final status:', json.dumps(status, indent=2))
            break
    except Exception as e:
        print('Status check failed:', e)
    time.sleep(3)

# Check final repo state
try:
    req = urllib.request.Request(f'http://localhost:8001/api/repositories/{repo_id}')
    resp = urllib.request.urlopen(req)
    repo = json.loads(resp.read().decode())
    print('Repo final:', json.dumps(repo, indent=2))
except Exception as e:
    print('Repo check failed:', e)
