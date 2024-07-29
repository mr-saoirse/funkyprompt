# https://ai.google.dev/gemini-api/docs/get-started/tutorial?lang=python

# https://ai.google.dev/gemini-api/docs/function-calling/tutorial?lang=python

# gemini-1.5-flash: our fastest multi-modal model
# gemini-1.5-pro: our most capable and intelligent multi-modal model

import google.generativeai as genai

# model = genai.GenerativeModel('gemini-1.5-flash')
# response = model.generate_content("What is the meaning of life?", stream=True)

# messages = [
#     {'role':'user',
#      'parts': ["Briefly explain how a computer works to a young child."]}
# ]
# response = model.generate_content(messages)


# model = genai.GenerativeModel('gemini-1.5-flash',
#                               # Set the `response_mime_type` to output JSON
#                               generation_config={"response_mime_type": "application/json"})
