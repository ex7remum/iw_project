const axios = require('axios');


const api_key = "SG_a5e178f46ae9bdb4";
const url = "https://api.segmind.com/v1/llama-v3p1-405b-instruct";

const data = {  

  "messages": [
    {
      "role": "user",
      "content" : "tell me a joke on cats"
    },
    {
      "role": "assistant",
      "content" : "here is a joke about cats..."
    },
    {
      "role": "user",
      "content" : "now a joke on dogs"
    },
  ]
};

(async function() {
    try {
        const response = await axios.post(url, data, { headers: { 'x-api-key': api_key } });
        console.log(response.data);
    } catch (error) {
        console.error('Error:', error.response.data);
    }
})();