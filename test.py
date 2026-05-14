import http.client
import json

conn = http.client.HTTPSConnection("https://dpapi.cn/v1")
payload = json.dumps({
   "model": "deepseek-v3",
   "messages": [
      {
         "role": "user",
         "content": "你好"
      }
   ]
})
headers = {
   'Authorization': 'Bearer sk-JilRMAofBA7Y2O9y4378347284F34a4b8c240c8bEe732fEe',
   'Accept': 'application/json',
   'Content-Type': 'application/json'
}
conn.request("POST", "/v1/chat/completions", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))