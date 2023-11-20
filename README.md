# Why funkyprompt?

See the docs [Funkyprompt docs](https://mr-saoirse.gitbook.io/funkyprompt/)

----

`funkyprompt` is a functional library for building predictable and scalable LLM agent systems over blob storage RAG stores. Lets unpick this

- agent systems are potentially powerful but hard to guide
- if you want to use your own data, you also need to organize those data
- you need your program to scale both in terms of managed complexity and data size

Today this is tricky for a bunch of reasons and `funkyprompt` takes a disciplined and thoughtful approach to evaluating a new way to build data stores and a new way to write programs.

`funkyprompt` is a functionally orientated way to make prompts for speaking with LLMs. As LLMs and building applications such as Retrieval Augmented Generation (RAG) systems exploded in activity, the ecosystem and tooling evolved incredibly quickly. `funkyprompt` takes a disciplined approach to constructing applications with one or multiple agents, by adhering to existing programming patterns, particularly functional ones, to construct applications.

Rather than build entirely new types of applications and dabbling in esoteric arts like Prompt Engineering, the idea is to point LLMs at your existing codebase (or a new codebase intended for Agent systems but written the way you normally would) to build programs and reason about program flow and construction.

This will make sense as we get into then specifics. For now, ask yourself this question; what if we do not write prompts at all? What if we rely on well documented code to create zero shot or conversational agents and even multi-agent systems? No prompts. No special "agent" libraries. Just business as usual.

`funkyprompt` is a cloud native library in the sense that it puts the data lake and the ability to run easily on the cloud front and center. There are many utilities for building RAG stores on data lakes. This allows for testing with functions that actually do CRUD on real data at any scale. For this reasons there are two reasons why you might use `funkyprompt`

## Usage

From this repo the easiest thing to do is use Poetry to build and install from the cloned repo. For more details see the docs to [Install](https://mr-saoirse.gitbook.io/funkyprompt/why-funkyprompt/install) and beyond.

## Roadmap

-
