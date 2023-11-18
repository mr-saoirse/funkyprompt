---
description: From installing to running a test command
---

# Install

You can do one of the following to start using funkyprompt.

1 Install from pypi

```bash
pip install funkyprompt
```

2 Or you can clone the latest code from the [repo](https://github.com/mr-saoirse/funkyprompt) and use [Poetry](https://python-poetry.org/) to build and install.&#x20;

```bash
#from within the repo folder run commands like these
poetry build
poetry install
```

You need the following ENV variables to be _optionally_ set depending on what you want to do

```bash
#required if you want to use the agent
export OPENAI_API_KEY=
#required for the S3 storage if using
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY= 
export AWS_DEFAULT_REGION=
```

Data is stored locally at `$HOME/.funkyprompt`&#x20;

If you are using S3 storage you should set the store home as

```bash
export FP_STORE_HOME=s3://<YOUR-BUCKET>/<some-dir>
```

***

To check the library is installed you could ask a question...

{% hint style="info" %}
Set an alias to make commands simpler. I am setting&#x20;

alias fp='poetry run fprompt' and running from a poetry virtual env
{% endhint %}

```bash
fp ask -q "What is the capital of ireland?"
```

This of course is not the reason why you would want to use `funkyprompt` - a slightly more interesting question is one that requires inspecting the code base for functions to answer the question. We have some example functions to make it easier to get started but it will be more fun if you bring your own. But for now

```bash
fp interpret -q "What would a person who likes cats more than dogs do?"
```

The out put will be something like below. We show a graphical representation of the functions to show the plan which is more relevant than what the answer is. The point of `funkyprompt` is to help the LLM navigate a code base to answer questions in a simple way.

```
answer: 
```

**Execution plan**

