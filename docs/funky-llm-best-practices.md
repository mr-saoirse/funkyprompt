---
description: How to get the most out of your LLM and funkyprompt
---

# Funky LLM Best Practices

Remember that LLMs are based on attention and next token prediction. You are trying to be efficient with what the LLM focuses on or not at any given time. This needs to become a science but sometimes it feels like a dark art. WE are going to look at some examples of things that work well to get some intuition and try to formalize it.

**1 When generating files like YAML files, ask the agent to add comments about what it is attending to at the top and throughout**&#x20;

This is not only great for debugging and understanding if we are setting the agent up for success, it also allows the agent to guide its generation. Its a Win-Win.&#x20;

Example:

**2 Be modular with guiding the agent in function prompts and dont try to add all the context in one place**

Its tempting to try to create one big super prompt but try to resit the urge. Add context gradually and test paths.&#x20;

Example:&#x20;
