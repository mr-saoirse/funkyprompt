# Why funkyprompt?

`funkyprompt` is a functionally orientated way to make prompts for speaking with LLMs. As LLMs and building applications such as Retrieval Augmented Generation (RAG) systems exploded in activity, the ecosystem and tooling evolved incredibly quickly. `funkyprompt` takes a disciplined approach to constructing applications with one or multiple agents, by adhering to existing programming patterns, particularly functional ones, to construct applications.

Rather than build entirely new types of applications and dabbling in esoteric arts like Prompt Engineering, the idea is to point LLMs at your existing codebase (or a new codebase intended for Agent systems but written the way you normally would) to build programs and reason about program flow and construction.

This will make sense as we get into then specifics. For now, ask yourself this question; what if we do not write prompts at all? What if we rely on well documented code to create zero shot or conversational agents and even multi-agent systems? No prompts. No special "agent" libraries. Just business as usual.

## Concepts

Designed as a lightweight library it is more about principles than features. You can extend it in your own library easily.
You can run it using REST or Webhooks
You can run it on Kubernetes

Types and functions are important. If we cannot describe something with types or functions we dont do it at all. There is only one simple agent class and it runs in a loop ny inspecting the space of functions and constructing a plan.
Simplicity is the key.

## Install

```bash
pip install funkyprompt
```

Or you can clone the project and do the poetry stuff..

```bash
poetry install funkyprompt

```

## Setup

In your environment you can set an OPEN_AI key to use the agents. This will allow you to run the tests on the example methods and types or your own

## Stores

We provide minimal support for data stores just to test the library to test RAG functionality. The objective is not to provide a connector for everything as some libraries do but provide one example of each type of store to illustrate the concepts. We follow the philosophy that if you have your favourite stores, you can use interfaces if your own to connect them into the functions described here.

You can set the following environment variables to a local directory or an S3 directory. If you use the S3 store you also need to make sure your have set your AWS keys. You need to create whatever bucket too.

```bash
export FP_STORE_HOME
#aws stuff
```

You can then test the stores by running scripts to load the sample data and running some prompts

Default homes are under `./funkyprompt/stores/`

```bash
fprompt query -q "What is X"
```

## Experiments

The primary point if fprompt is to run experiments to prove patterns for predictable results. Visit the docs to learn more.

## Auditing

We write all logs as EVENT in the logger
You can add callbacks to the logger to send data wherever - data are usually written as structured pydantic types
The sessions is always dumped to the vector store
Pulsar can be used on the cluster
Monologue can scrape data from logger

## Buildpack

## Conventions

FP uses modules in MODULE_HOME such as ops.examples or whatever you specify.
All types are expected to live under this directory MODULE_HOME/NAMESPACE/TYPE
Crud and methods associated with the entity can be added here
We may generated `_entity_crud.py` which the user can update or any other ops can be added
we prefix auto generated files (except for initial types) with the under score to observe that its not safe to update and re-run generators that could overwrite
Docstrings format - use the helper to generate for a given function - it also validates that typing info is present
