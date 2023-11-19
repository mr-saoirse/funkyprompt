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

We currently have a columnar data store wrapping [DuckDB](https://duckdb.org/) and a vector store wrapping [LanceDB](https://lancedb.github.io/lancedb/) - see also [lance docs](https://lancedb.github.io/lance/)). Conveniently you can use these locally or with an S3 backend. If you want to use the S3 backend set the env var `FP_STORE_HOME` as described in [install.md](install.md "mention") but most of the tutorials assume you want to run things locally first.

***

To understand how to use the data stores, lets take a quick tour and then you can maybe check out some of the other [Broken link](broken-reference "mention")

### How it works

#### Unstructured data&#x20;

To get started lets just ingest data from a URL. We will embed the data with the default embedding (see tutorials to choose other embeddings). The CLI is useful for testing but you will want to take a look at the code e.g. in a Jupyter notebook. We find its nice to be able to just get a feel via the cli.

{% hint style="info" %}
For this section set an alias to funky prompt called "fp" as described in the installation
{% endhint %}

{% code overflow="wrap" %}
```bash
fp ingest page --url "https://www.gutenberg.org/files/20748/20748-h/20748-h.htm" -n FairyTales
```
{% endcode %}

Give it a moment to read the page and embed it in a vector store table called fairy tales

{% hint style="info" %}
This will be stored in `$FP_STORE_HOME/stores/vector/default/FairyTales`

`The namespace here is default as it was not specified`
{% endhint %}

Now that we have ingested the data we can ask questions. The interpret will consult a number of stores by default and can be tuned, which will be the topic of another tutorial. In this case we have only one data store so lets not think about it too much

```
fp agent interpret -q "Who was sinbad and where did he retire?"
```

**Structured Data**

In one respect, unstructured data is more interesting. This is how we load tonnes of arbitrary text into our systems and let the agent figure it out. However, _types_ play an enormous role in `funkyprompt` , firstly as a way to guide agents and secondly as a way to store columnar data that is used in type systems. Actually even the unstructured data is represented as a Pydantic type called `AbstactContentModel` which describes how to embed and store the data in the vector store. However, more generally, we can ingest arbitrary types into our system. Lets consider scraping structured types with some quantitative data from a website in three steps.

_1 Initialize the type with a sample_

I picked a random Kaggle dataset for [Indonesian Food and Drink Nutrition](https://www.kaggle.com/datasets/anasfikrihanif/indonesian-food-and-drink-nutrition-dataset) and downloaded it. To explain how this works - the first thing we do is read some data. Here I am using Polars.

```python
from funkyprompt.model import AbstractModel
import polars as pl
df = pl.read_csv('/Users/sirsh/Downloads/nutrition.csv')
```

<figure><img src="../.gitbook/assets/image.png" alt=""><figcaption><p>sample data</p></figcaption></figure>

In `funkyprompt` we need Pydantic objects and we can create a dynamic one with a name and namespace (default is "default")&#x20;

{% code overflow="wrap" %}
```python
Model = AbstractModel.create_model_from_pyarrow('NutritionSample',     py_arrow_schema=df.to_arrow().schema)
```
{% endcode %}

We can create a store from this Model and add the records&#x20;

```python
records = [Model(**r) for r in df.to_dicts()]
store.add(records)
```

_2 Ask some questions_

When working with stores, the first thing you can do is ask a direct question of the store which is just a search. In the case of the Columnar store, we actually use an LLM to turn the question into a query but the result is still just a search. The Vector store will just do a vector search on the content embeddings. We can test this new store with

```
store('What is Labu Air')
```

Now to try with an agent

```
#by default the store.as_agent disables fucntion search so we can test the store
#but in this example we want to lookup the describe_image function
ag = store.as_agent(allow_function_search=True)
ag("How many calories does Labu Air have - please describe the image")
```

{% hint style="info" %}
Answer:

{% code overflow="wrap" %}
```
The calories in Labu Air (bottle gourd) are 17 calories per serving. The image associated with Labu Air shows three bottle gourds on a white wooden surface, with two whole gourds and one that is partially sliced into round pieces. The sliced pieces reveal the white flesh and seeds of the gourd, arranged in a fan shape. The gourds have a smooth, green skin and are cylindrical, tapering at the ends, against the contrasting rustic background of the wooden surface.

To find this information, I initiated a search for functions that could help answer your query, considering that Labu Air could refer to a type of food or a term that might not be immediately familiar. Based on the functions provided, I called the "run_search" function to look up the caloric content of Labu Air. After obtaining the nutrition info, I used the "entity_key_lookup" function to find the associated image, which I then analyzed using the "describe_visual_image" function to provide a description of the image associated with Labu Air.
```
{% endcode %}
{% endhint %}

GPT-4 is able to insect images which is nice - so if we did not supply the describe\_image function then we might with some link get a response (somehow it tricks the are-you-human captcha on that link!). But above to control the image description via `funkyprompt` we also have a function that describes the image via the vision model that the agent can use. That is what you see in the response above.

***

With that we have seen two examples of ingesting data and asking questions. But to build really interesting systems, we first need to understand functions and how `funkyprompt` actually works. Then we can come back and ingest a lot more data and ask a lot more questions! Buckle up.
