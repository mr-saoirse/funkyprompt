from funkyprompt.core import AbstractModel, Field
import typing

DESCRIPTION = f"""The query classifier is used to determine the nature of a natural language query.
1. If entities are mentioned, then it could be a key look therefore extract entities in the question is important
2. If the question consists of multiple orthogonal elements, it could be split into separate questions
3. if the user asks for lists or statistic of some kind OR refer to something in the object schema then they probably want to run an SQL type or Tabular type of query which you can construct as a select statement with predicates, aggregates etc. Do not guess any field names in constructing SQL queries.
4. if the user asks for something more descriptive then a vector search may be most useful
5. In some complex cases a (cypher) graph query might be the most useful IF the schema of the graph is know. 
  If someone wants to know about things that are "related" to some topic or node or entity that a Cypher query is possibly valid.
  You should not add labels to nodes or edges unless you have seen form the schema that they exist and you should use `name` as the key attribute.
  For cypher queries based on relations use `MATCH (n)-[r]->(m) WHERE m.name = 'NAME-HERE' RETURN n, label(n) as label`

*How to classify*
- It is useful to emphasize entities if they exist as a high value query input. 
  - Broad topics such as 'programming' or 'cities' are not considered as entities, entities should be specific  like Order123 or New York
- if you are confident about an SQL query this could also yield a high value result for the user
    - confidence calibration is important. If there is any table, column or value that you have 
    guessed and not seen in the entity mode your confidence should be less that 0.75
    - you should NEVER use the user's question as evidence for the existence of a table or field since they have no knowledge of the data schema
- Otherwise, mention if the question require vector search because the text is to vague or you do not have enough domain semantic context
  - it is useful to decompose questions for multiple vector searches can be run
- Graph (cypher) queries are used for some complex edge vases

"""

# Notes: a big part of this is lowering the confidence on SQL


class QueryClassifier(AbstractModel):
    class Config:
        name: str = "query_classifier"
        namespace: str = "core"
        description = DESCRIPTION
        MIN_QUERY_CONFIDENCE = 0.84

    sql_query: typing.Optional[str] = Field(
        description="Provide a postgres dialect SQL for tables that match entities you know about only. The users question is not evidence of existence.",
        default_factory=list,
    )
    sql_query_confidence_based_on_model: typing.Optional[float] = Field(
        description="You should NEVER use table names, fields or predicate values that you have no evidence for in the Entity Model provided. The user's question is not evidence. Low scores are < 0.85",
        default=0.0,
    )
    confidence_comments: typing.Optional[str] = Field(
        description="explain reasons for lack of confidence.",
        default_factory=list,
    )
    cypher_query: typing.Optional[dict] = Field(
        description="Provide a cypher query AND your confidence in the query. Low confidence queries i.e. those that lack evidence in input schema will be ignore. scored as a percentage",
        default_factory=dict,
    )
    entities: typing.List[str] = Field(
        description="List of entities in the input question. Entities should NOT be general nouns or topics but specific identifiers or places or people with identity",
        default=None,
    )
    decomposed_questions: typing.List[str] = Field(
        description="The users question(s) decomposed into one or more questions"
    )

    entity_model_type: typing.Optional[str] = Field(
        default=None, description="The fully qualified model entity type if known"
    )
    recommend_query_type: str = Field(
        description="VECTOR|SQL|ENTITY|GRAPH", default=None
    )

    @classmethod
    def _classify_question_as_query_for_model(
        cls,
        model: AbstractModel,
        question: str,
        preview: bool = False,
        return_model: bool = True,
    ) -> "QueryClassifier":
        """Used to classify a question based on a model semantics.
        use the preview flag to see the prompt markdown
        use the return_model=False to have the model be more verbose in testing (see its thought process)

        Args:
            model: The model type providing semantics
            question: the user's question tp classify
            preview: this shows the generated prompt (best viewed as Markdown)
            return_model: the default returns the pydantic object for the classification and asks the language model for JSON
        """

        from funkyprompt.services.models import language_model_client_from_context
        from funkyprompt.core.agents import LanguageModel, CallingContext

        plan = f"""Below you are given details about ane entity model. 
This semantic information corresponds to a table with the given fields some of which can be searched with vector search. 
Entity lookup is possible for the name field if known. 
You should use the Query Classifier Model below [A] to provide a classification for the *question* in the context the model [B]

# User's Question
```
{question}
```

# [A] Query Classifier System prompt

{cls.get_model_as_prompt()}

# [B] Entity model
_(Use this entity model to construct a specific query classification for the model)_

{model.get_model_as_prompt()}

"""

        if preview:
            return plan

        lm_client: LanguageModel = language_model_client_from_context()

        data = lm_client(plan, context=CallingContext(prefer_json=return_model))

        if return_model:
            return cls.model_validate_json(data)
        return data
