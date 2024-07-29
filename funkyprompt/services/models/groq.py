# https://github.com/groq/groq-python

from groq import Groq

# https://console.groq.com/docs/models
model = "llama3-8b-8192"

# SET: GROQ_API_KEY
# client = Groq()

# model = "llama3-8b-8192"

# chat_completion = client.chat.completions.create(
#     messages=[
#         {
#             "role": "user",
#             "content": "Explain the importance of low latency LLMs",
#         }
#     ],
#     model="llama3-8b-8192",
# )
# print(chat_completion.choices[0].message.content)
