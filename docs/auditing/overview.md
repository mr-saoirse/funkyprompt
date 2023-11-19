# Overview

Auditing is a core component of `funkyprompt.` The curation of data and functions beyond Day 1 problems relies on good telemetry and storing history. Every session is stored in your local store allowing is to track question-response pairs and the agents confidence. We always ask the agent ti report strategy and confidence in every session. Beyond this, we want to understand how functions are loaded and how data in general are loaded. That is why we track all the store\_ids and record\_ids that are used in answering questions. These data can then be used to improve how we index and fragment data stores and polymorphic functions over them.

We support OpenTelemetry as a standard way to do metrics, tracing and logging. The rough data model we are tracking is&#x20;

* InterpreterSession (user, channel, question, answer, confidence, session\_id)
* Functions (Function loading events in terms of context, function, distance sets
* DataPoints (for each question context, the set of ids retrieved with any distance)

Note that the last two are similar. Functions are just a special type of data. Generally we want to understand for a given session, with a master question, this divides into sub questions. For each of these sub questions, we want to understand what group of data are returned. For each data point we want its distance. This is something lile

```
sub_context, [(ID,Distance), (ID,Distance), etc. ]
```

After we collect all of these data we can use it to learn how best to organize stores. Organization means doing things like chunking content within stores or chunking stores themselves. Store chunking could mean split one store into many or many into one to optimize retrieval.&#x20;
