---
description: The best prompts are no prompts
---

# Why funkyprompt

The LLM and LLM tool space is noisy so we hesitantly introduce a new and simple tool into this space. The goal is to focus on powerful predictability. This is done by respecting the interface between (a) the LLM such as OpenAI chat completions with functions interface and (b) everything else i.e. our code.

`funkyprompt` works by exploring how we can write code as we normally would, with typing and docstrings, avoid writing prompts at all and yet still creating powerful agent systems.

At the core we run a single interpreter that interfaces our code to the LLM, which basically loops and tries to solve problems, while calling out to supplied functions. But its a bit more exciting than that. This is a pattern that subsumes zero shot, conversational, planning and multi agent systems in a purely functional way.&#x20;

The library provides tools for understanding how the LLM inspects our functions and plans. It explores where the LLM does well and where it trips up.&#x20;



#### Some nice things about funkyprompt

1. Fast setup with data stores, data and LLM interface ready to go (tutorial)
2. Easy tools to ingest real or test data into the stores to experiment with (tutorial)
   1. Use local or S3 storage with no configuration beyond env variables
3. Strongly typed and functional - everything is either pydantic or a function (tutorial)
4. Beyond prototyping, use it in your libraries or deploy it to your cloud as a service (tutorial)
5. Lots of sample data and examples to work with (tutorial)
6. Clear guide lines for writing agent programs without having to learn any tools. (tutorial)
7. backed by extensive research and tests on use cases (tutorial, notebooks, articles)

## Install

## CLI

## Serve

## Deploy to Coud

## Where next?

<table data-view="cards"><thead><tr><th></th><th></th><th></th></tr></thead><tbody><tr><td></td><td><a data-mention href="broken-reference">Broken link</a></td><td></td></tr><tr><td></td><td><a data-mention href="broken-reference">Broken link</a></td><td></td></tr><tr><td></td><td><a data-mention href="broken-reference">Broken link</a></td><td></td></tr></tbody></table>
