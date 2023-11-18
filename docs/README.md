---
description: The best prompts are no prompts
---

# Why funkyprompt

The LLM and LLM tool space is noisy so we hesitantly introduce a new yet simple tool into this space. The goal is to focus on _powerful predictability_ when building agent systems. We want to be able to gradually _engineer_ increasingly complex systems without sacrificing determinism as we combine LLMs with our code and data.

`funkyprompt` takes the stance that this is done by respecting the interface between (a) the LLM (such as OpenAI chat completions with functions) and (b) everything else i.e. our code.&#x20;

{% hint style="info" %}
If you ask yourself what is the hard part of building data-driven agent systems your answer might span from (a) improving LLMs towards AGI, (b) controlling and guiding  agents and multi-agents and (c) engineering data and interfaces. Funkyprompt deals with (c). Moreover, unlike a world where we have one or two monolithic databases or sources, it considers how to easily creating many specialist stores and wire them together. We believe that this one critical and hard part of building agent systems.&#x20;
{% endhint %}

`funkyprompt` works by exploring how we can write code i.e. functions  as we normally would, with typing and docstrings. It tries to avoid tinkering with prompts  and yet still create powerful agent systems.  At the core we run a _single interpreter loop_ that interfaces between our code to the LLM. It tries to solve problems, plan and answering questions by calling out to supplied functions. It is a simple pattern that subsumes zero shot, conversational, planning and multi agent systems in a purely functional way.&#x20;

The `funkyprompt` library provides tools for understanding how the LLM inspects our functions and plans. This is all data over data. The library makes it easy to ingest data and experiment with building agent systems over data. &#x20;

***

#### Some nice things about funkyprompt

1. Fast setup, with data stores, data and LLM interface ready to go (tutorial)
2. Easy tools to ingest real or test data into the stores to experiment with (tutorial)
   1. Use local or S3 storage with no configuration beyond env variables
3. Strongly typed and functional - everything is either pydantic or a function (tutorial)
4. Beyond prototyping, use it in your libraries or deploy it to your cloud as a service (tutorial)
5. Lots of sample data and examples to work with (tutorial)
6. Clear guidelines for writing agent programs without having to invest in any frameworks. (tutorial)
7. Backed by extensive research and tests on use cases (tutorial, notebooks, articles)

## Getting Started

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td></td><td><a data-mention href="why-funkyprompt/install.md">install.md</a></td><td></td><td><a href="why-funkyprompt/install.md">install.md</a></td></tr><tr><td></td><td><a data-mention href="why-funkyprompt/deploy.md">deploy.md</a></td><td></td><td></td></tr><tr><td></td><td><a data-mention href="why-funkyprompt/rag-systems.md">rag-systems.md</a></td><td></td><td></td></tr></tbody></table>

