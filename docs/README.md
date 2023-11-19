---
description: The best prompts are no prompts
---

# Why funkyprompt

`funkyprompt` is a function registry and data store for working with LLMs.

The LLM and LLM tool space is noisy, so it is with some hesitation that we introduce a new tool into this space. However it is a simple tool that is more about exploring best practices without imposing any architectural changes on your existing system. Providers of LLMs such as OpenAI will increasingly abstract their systems and as they do, we will want a fully managed and searchable registry of functions to build agent systems. `funkyprompt` explores this interface.&#x20;

The goal is to focus on _powerful predictability over federated data_ when building agent systems. We want to be able to gradually engineer increasingly complex systems without sacrificing determinism as we combine LLMs with our code and data.

`funkyprompt` takes the stance that this is done by respecting the evolving interface between the LLM (such as OpenAI chat completions with functions) and everything else i.e. our code.&#x20;

{% hint style="info" %}
If you ask yourself what is the hard part of building data-driven agent systems your answer might span from (a) improving LLMs towards AGI, (b) controlling and guiding  agents and multi-agents and (c) engineering data and interfaces. Funkyprompt deals with (c). It considers how to create many specialist data stores and wire them together in agent systems. We see this as an isolated critical part of building agent systems.&#x20;
{% endhint %}

`funkyprompt` works by exploring how we can write functions as we normally would, with _typing_ and _docstrings_ and make it easy for agents to use them to find the data and behaviors they need. It tries to avoid tinkering with prompts while still create powerful and dynamic agent systems.  At the core we run a _single interpreter loop_ that interfaces between our code to the LLM. It tries to solve problems, plan and answer questions by calling out to supplied functions. We try not to rely on extensive prompting on. a case by case basis but rely on the descriptions of functions and stores. It is a simple pattern that subsumes zero shot, conversational, planning and multi agent systems in a purely functional way. We hope that it will allow for more mdoualirty and ultimately robustness when building agent systems.&#x20;

The `funkyprompt` library provides tools for understanding how the LLM inspects our functions and plans. The library makes it easy to ingest data and experiment with building agent systems over data. &#x20;

***

#### Some nice things about funkyprompt

1. Fast setup, with data stores, data and LLM interface ready to go&#x20;
2. Easy tools to ingest real or test data into the stores to experiment with&#x20;
   1. Use local or S3 storage with no configuration beyond env variables
3. Strongly typed and functional - everything is either pydantic or a function&#x20;
4. Beyond prototyping, use it in your libraries or deploy it to your cloud as a service&#x20;
5. Lots of sample data and examples to work with&#x20;
6. Clear guidelines for writing agent programs without having to invest in any frameworks. (tutorial)
7. Manage experimental data to turn retrieval augment agent systems into a more predictable endeavor

## Getting Started

<table data-view="cards"><thead><tr><th></th><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td></td><td><a data-mention href="why-funkyprompt/install.md">install.md</a></td><td></td><td><a href="why-funkyprompt/install.md">install.md</a></td></tr><tr><td></td><td><a data-mention href="why-funkyprompt/deploy.md">deploy.md</a></td><td></td><td></td></tr><tr><td></td><td><a data-mention href="why-funkyprompt/rag-systems.md">rag-systems.md</a></td><td></td><td></td></tr></tbody></table>

