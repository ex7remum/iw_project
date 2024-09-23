import requests
import json

def make_request(message_content, language="en",
                 region='us-central1', 
                 endpoint='https://us-central1-aiplatform.googleapis.com',
                 model='meta/llama3-405b-instruct-maas'):
    """Отправка запроса на API с curl-like функциональностью"""
    

    with open('request_info.json', 'r') as file:
        request_data = json.load(file)
    
    project_id = request_data['PROJECT_ID']
    access_token = request_data['ACCESS_TOKEN']

    url = f"https://{endpoint}/v1beta1/projects/{project_id}/locations/{region}/endpoints/openapi/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": message_content,
                "language": language  # Параметр языка
            }
        ]
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code}, {response.text}")
        return None
