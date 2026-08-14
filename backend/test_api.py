import urllib.request
import urllib.error
import json

try:
    req = urllib.request.Request(
        'http://localhost:8001/api/repositories',
        data=json.dumps({'github_url': 'https://github.com/octocat/Hello-World'}).encode(),
        headers={'Content-Type': 'application/json', 'X-API-Key': 'rie_dev_api_key'}
    )
    resp = urllib.request.urlopen(req)
    print('Status:', resp.status)
    print('Body:', resp.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP Error:', e.code)
    print('Body:', e.read().decode())
except Exception as e:
    print('Error:', e)
