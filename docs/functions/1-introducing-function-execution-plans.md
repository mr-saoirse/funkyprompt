---
description: How we audit and visualize function call planning and execution
---

# 1 Introducing Function Execution Plans

We want to understand how the LLM understands the function repertoire that we provide it. We want to tinker with the questions to see what it _attends_ to and where it does well or trip up. We want to nail down _function signatures_ and make sure the LLM always respects them. We want to _audit_ and _visualize_ what is going on as we build in more complexity and more data without losing our way. Lets get into it!



**In this section lets look at;**

1 Ranking functions with respect to questions

2 Building a function execution [DAG](https://en.wikipedia.org/wiki/Directed\_acyclic\_graph)&#x20;

***

{% hint style="info" %}
The funkyprompt default agent has built in functions loaded. A good way to see what is going on is to look at these - this returns `FunctionDescription` objects

```
funkyprompt.agent._built_in_functions
#you can look at one of these and call the .function_dict() 
#that returns the function metadata that we pass to OpenAI
```
{% endhint %}

A good way to begin understanding the power of functions is to ask the agent to construct a plan about what it _would_ do for some simple questions and a sample repertoire of functions.&#x20;

Asking it to rank functions and construct execution graphs is a good way to see how we need to write function descriptions and the interpreter logic. For example, a methodology for how to describe and chain return types, how to know what sorts of outputs from what function are compatible as inputs to another function are all good things to see in the plan. Lets look at some examples.

_Example question for build in examples_

{% code overflow="wrap" %}
```bash
fp agent plan -q "Can we find something with a high rating to cook at home that our guests Snow White and Sinbad would like and if not, where would we take them to dine out?"
```
{% endcode %}

This entry point ranks and plans.

The execution graph can take different forms, this is one example using YAML which is compact and structured. This would be a good representation to generate DAGs in general.

{% code overflow="wrap" %}
```json
- function name: get_information_on_fairy_tale_characters
  context: "Getting likes and dislikes of Snow White and Sinbad"
  confidence: 80
  args: 
    - name: question
  value: $question
  example_function_call_args:
      question: "What do Snow White and Sinbad like to eat?"

- function name: get_recipes_with_ratings
  context: "Find high-rated recipes for the preferred dishes of Snow White and Sinbad"
  confidence: 90
  args: 
    - name: what_to_cook
      value: $get_information_on_fairy_tale_characters.output.favourite_food
    - min_rating: 4.5
  example_function_call_args:
      what_to_cook: "Apple pie"
      min_rating: 4.5
      
- function name: get_restaurant_reviews
  context: "Find a suitable restaurant to dine-out, if cooking at home wasn't an option"
  confidence: 80
  args: 
    - name: name_or_type_of_place
      value: $get_information_on_fairy_tale_characters.output.favourite_cuisine
  example_function_call_args: 
      name_or_type_of_place: "Italian"
```
{% endcode %}

This execution graph could then be called in a single step in the iteration loop rather than making successive calls. This is part of the `funkyprompt` principle of "separate our code from the LLM over well defined interface".&#x20;

The confidence is important here because if we had  a very large set of functions, this is filtering the list to what is shown in the graph here. The extended output is now shown here but you can try for yourself with your own functions and questions. For example you could have hundreds of functions and only select `m from n` for evaluation in the graph.&#x20;

An important part of `funkyprompt` is how the possible functions can be continuously revised during an interpret loop.

{% hint style="info" %}
Although they may seem of secondary important, the `example_function_call_args` are very important in the planning because they show that the function describes what sorts of inputs and outputs it expects. If you used in correct types or comments in your function, this should be exposed here. It tells us we are not communicating properly with the LLM.
{% endhint %}

**dag-order**

We can introduce the order of a graph or DAG order so that we can run some things in parallel. The execution graphs are generated by the LLM so its very nice to see how it suggests a nice structured format in the context of the question and the functions. The prompt asks for comments to. I introduce some functions that are essentially the same and tell the agent it can use lower value functions if they can be run in parallel anyway.

We can work with this!

```yaml
# Yaml execution plan

# - functions.get_information_on_fairy_tale_characters to get info about characters.
# - functions.get_recipes_with_ratings to get highly rated recipes if we can cook something they would like.
# - functions.get_restaurant_reviews & functions.get_restaurant_reviews_other for in case we need to take them out instead.

# start by figuring out what the characters could like
- function_name: functions.get_information_on_fairy_tale_characters
  context: "Find out preferences of Snow White and Sinbad"
  dag-order: 0 # This function is the first to be called, no dependencies.
  confidence: 80
  args: 
    - question: "Can Snow White and Sinbad like similar things?"
  example_function_call_args: 
    - question: "What foods do Snow White and Sinbad like?"

#Depending on output of the above, either we cook at home:
- function_name: functions.get_recipes_with_ratings
  context: "Find highly rated recipe that match characters preferences"
  dag-order: 1 # Depends on output of first function
  confidence: 100
  args: 
    - what_to_cook: $get_information_on_fairy_tale_characters.output
    - min_rating: 4.5
  example_function_call_args: 
    - what_to_cook: Apple_Pie
    - min_rating: 4.5

# Or we find a suitable place to take them out:
- function_name: functions.get_restaurant_reviews
  context: "Find a restaurant with good reviews serving food Snow White and Sinbad would like"
  dag-order: 1 # Can execute in parallel with get_recipes_with_ratings as both depend on first function output
  confidence: 70
  args: 
    - name_or_type_of_place: $get_information_on_fairy_tale_characters.output
  example_function_call_args: 
    - name_or_type_of_place: Apple_Pie_Parlor

- function_name: functions.get_restaurant_reviews_other
  context: "Further information about potential places to visit for meal"
  dag-order: 1 # Can execute in parallel with both above as all three depend on first function output
  confidence: 80
  args: 
    - name_or_type_of_place: $get_information_on_fairy_tale_characters.output
  example_function_call_args: 
    - name_or_type_of_place: Apple_Pie_Parlor

# Comments and considerations.
# - I prioritised having a plan to either find a recipe to cook at home, or places to eat out. Cook at home scenario depends on whether we can find a suitable highly rated recipe.
# - Ensured parallel execution where possible.
# - Variables were passed between functions according to required inputs and outputs. I kept inputs to be the outputs of previous function.
# - Assumed that the AI has specific information about the characters and their likings.
```

In this case we allow for low value functions to be called if they can be run in parallel with higher value functions. This is an _opportunistic_ approach given that we can run our code without LLM round trips. OF course, we still have to be careful with context size in the response but we could filter that in code e.g. taking the confidence into account.&#x20;

{% hint style="info" %}
A desirable property is low DAG depth. Here we have 5 functions in 2 layers. Thats nice.
{% endhint %}

Before we move into more complex plans, here is a record of the PLAN that was used for this agent. The idea of `funkyprompt` is to provide a starting prompt but then use the function comments to extend the context. Generally the initial prompt should be _minimal and stable_ but in this case we are experimenting with the idea of planning and seeing what works and what does not.&#x20;

```python
# we typically just use one agent in funkyprompt but we can create other classes with alternate plans
class PlanningAgent(AgentBase):
    VIZ = "Yaml"
 
    PLAN = f""" 
 You are function using and planning agent. proceed with the following steps:"
 1. Consider the question lookup function to find available functions that might help.
 2. From all the functions, list each function with a rating from 0 to 100 with brief explanation for your rating. (You should favour functions that provide general output values over specific output values for the same entity).
 3. Using each of the most useful functions *AND ALSO* lower ranked functions IF AND ONLY IF they could be run in parallel, construct a single (commented) {VIZ} graph representation over all paths as a nested chain of *individual* functions you would call passing arguments between functions. 
    Add the following attributes for each function call
    - function_name:
    - context: the reason for calling the function. this should be quoted string literal value.
    - dag_order: functions have the same dag-order if they could be executed in parallel otherwise they have a higher g-order. Please add a code comment above this attribute to explain the order and dependencies.
    - confidence: (in choosing this function).
    - args: the name of the function args and the value in the execution graph. for example an arg value in a graph could be a literal or a graph variable $name_of_function.output  
    - example_function_call_args: in addition to adding the function call args, provide *literal* example mapping for each arg. these literal examples should help you think about the variables you are passing around and if the inputs should be long-form text or structured primitives or object types 
 4. Add your "attention comments" to the top of the generated {VIZ} graph output listing the things you attended to as bullet points.
  *Special note*: the key step to attend to is how to chain args for the right functions together in step 3 - You must think about what types of inputs and outputs you are dealing with and use variables correctly as you pass variables from earlier steps to later steps. 
 """
     USER_HINT = "Please return to me the graph representation (in the correct format) about the plan with respect to the question asked. "
```

Ok, lets check out the mechanics of executing these simple plans.