#pip install cerebras_cloud_sdk
import os
from cerebras.cloud.sdk import Cerebras

client = Cerebras(
    # This is the default and can be omitted
    api_key=os.environ.get("CEREBRAS_API_KEY"),
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Why is fast inference important?",
        }
],
    model="llama3.1-8b",
)

print(chat_completion)


# stream = client.chat.completions.create(
#     messages=[
#         {
#             "role": "user",
#             "content": "Why is fast inference important?",
#         }
#     ],
#     model="llama3.1-8b",
#     stream=True,
# )

# for chunk in stream:
#     print(chunk.choices[0].delta.content or "", end="")

# {
#   "tool_call": {
#     "id": "call_xyz789",
#     "name": "evaluate_expression",
#     "parameters": {
#       "expression": "25 * 4 + 10"
#     }
#   }
# }
