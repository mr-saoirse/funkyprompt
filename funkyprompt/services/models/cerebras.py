# import os
# from cerebras.cloud.sdk import Cerebras

# client = Cerebras(
#     # This is the default and can be omitted
#     api_key=os.environ.get("CEREBRAS_API_KEY"),
# )

# chat_completion = client.chat.completions.create(
#     #response_format= {"type": "json_object" },
#     messages=[
#         {
#             "role": "system",
#             "content": Plan.get_model_as_prompt()
#         },
#         {
#             "role": "user",
#            # "content": "I will respond in a json format using the Structured Response format in the prompt respecting the exact schema for the nested objects. I will not add additional comment and respond only in fenced json with a single DAG object e.g. ```json MY_NESTED_JSON```"
#             "content": "please respond to my question using the structured format provided. The type tables show a possibly nested structure that can be a JSON object graph. You should respect the schema by thinking step by step how to generate the structured graph to answer my question and you shoudl always respond in fenced json"
#         },
#         {
#             "role": "user",
#             "content": 'Please provide a plan to show what is in my diary and then generate and save new tasks  '
#         }
# ],
#     model="llama3.1-8b",
# )
# a = chat_completion.choices[0].message.content
 


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
