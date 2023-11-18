---
description: Adding and using data in funkyprompt
---

# RAG systems

Software and data are not really separable these days. The motivation for building `funkyprompt` was really to build data-rich systems with LLM based agents sitting on top. The functions we are dealing with are often, but maybe not always, functions that read data. This puts _Retrieval Augmented Generation_ (RAG) at the heart of things.

One useful thing about `funkyprompt` is the RAG is essentially "built in". This is because we use blob-storage-centric data stores so that everything is "embedded".&#x20;

{% hint style="info" %}
A note about embedding databases and S3 blob storage:
{% endhint %}

If you are as excited about embedded (vector) databases as we are, you will love `funkyprompt`

We currently have a columnar data store wrapping [DuckDB](https://duckdb.org/) and a vector store wrapping [LanceDB](https://lancedb.github.io/lancedb/) - see also [lance docs](https://lancedb.github.io/lance/)). Conveniently you can use these locally or with an S3 backend. If you want to use the S3 backend set the env var `FP_STORE_HOME` as described in [install.md](install.md "mention").

***

To understand how to use the data stores, lets take a quick tour and then you can maybe check out some of the other [Broken link](broken-reference "mention")

### How it works

#### Unstructured data&#x20;

To get started lets just ingestion data from a URL. We will embed the data with the default embedding (see tutorials to choose other embeddings). The CLI is useful for testing but you will want to take a look at the code base e.g. in a Jupyter notebook. We find its nice to be able to just get a feel via the cli.

{% hint style="info" %}
For this section set an alias to funky prompt called "fp" as described in the installation
{% endhint %}

```bash
fp ingest page --url "" -n fairy-tales
```

Give it a moment to read the page and embed it in a vector store table called fairy tales

{% hint style="info" %}
This will be stored in $`FP_STORE_HOME/stores/vector/default/fairy-tales`

`The namespace here is default as it was not specified`
{% endhint %}

Now that we have ingested the data we can ask questions. The interpret will consult a number of stores by default and can be tuned which will be the topic of another tutorial. In this case we have only one data store so lets not think about it too much

```
fp agent interpret -q "Who was sinbad and where did he retire?"
```

**Structured Data**

In one respect, unstructured data is more interesting. This is how we load tonnes of arbitrary text into our systems and let the agent figure it out. However, types play an enormous role in `funkyprompt`  firstly as a way to guide agents and secondly as a way to store columnar data that is used in type systems. Actually even the unstructured data is represented as a Pydantic type called `AbstactVectorStoreEntity` which describes how to embed and store the data in the vector store. However, more generally, we can ingest arbitrary types into our system. Lets consider scraping structured types with some quantitative data from a website in three steps.

_1 Initialize the type with a sample_

_2 Scrape some examples from the site into our RAG store_

_3 Ask some questions_



***

With that we have seen two examples of ingesting data and asking questions. But to build really interesting systems, we first need to understand functions and how `funkyprompt` actually works. Then we can come back and ingest a lot more data and ask a lot more questions! Buckle up.
