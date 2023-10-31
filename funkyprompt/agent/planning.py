from .AgentBase import AgentBase


class PlanningAgent(AgentBase):
    """
    simple planning agent; interesting things to consider are
    - what is the zero shot planning horizon and how we iterate (regrouping)
    - structured representation of plans
    - loading and purging functions and context
    - materializing functions to fill gaps in plan execution (small worlds)
    - a key thing is known when functions take one word or context type inputs because for vector stores is large in large out but for many functions we need simple tokens
    - **contravariance and covariance, specificity vs generality, vector vs otherwise**

    example question:
     fp agent plan -q "find out Eunseo's favourite thing and then decide where to bring her for dinner"

    Here is an example graph it produced. I like the variable notation - its stigmergic
    But the reasoning is not perfect.

    JSON graph representation:

    ```json
    {
    "functions":[
        {
            "name":"get_information_on_fairy_tale_characters",
            "args":{
                "question":"What are the favourite foods of Snow White and Sinbad?"
            },
            "next":{
                "name":"get_persons_favourite_thing_of_type",
                "args":{
                "person":"${get_information_on_fairy_tale_characters.result}",
                "thing_type":"food"
                },
                "next":{
                "name":"get_restaurant_reviews",
                "args":{
                    "name_or_type_of_place":"${get_persons_favourite_thing_of_type.result}"
                }
                }
            }
        }
    ]
    }
    ```

    JSON graph representation:

    ```json
    {
    "get_information_on_fairy_tale_characters": {
        "args": {
        "question": "What do Snow White and Sinbad like to eat?"
        },
        "chain": {
        "get_restaurant_reviews": {
            "args": {
            "name_or_type_of_place": "<favourite food from fairy tale characters>",
            "location": "<location>"
            },
        }
        }
    }
    }
    ```

    """

    VIZ = "JSON"
    VIZ = "visual"
    VIZ = "yaml"
    # comment on how you might use the function and what entity the function describes. remove this from the notes in step 2 to save context window ??
    # we want a brief note because when the function is overlooked we need to know why
    # its vary nice to embed attention comments into the YAML for conciseness and it may help the agent too
    PLAN = f""" You are function using and planning agent. proceed with the following steps:"
                1. Consider the question and lookup function to find available functions that might help.
                2. From all the functions, list each function with a rating from 0 to 100 with brief explanation for your rating. (You should favour functions that provide general output values over specific output values for the same entity).
                3. Using each of the most useful functions *AND ALSO* lower ranked functions IF AND ONLY IF they could be run in parallel.
                   Construct a single (commented) {VIZ} graph representation over all paths as a nested chain of *individual* functions you would call passing arguments between functions. 
                   Add the following attributes for each function call
                   - function_name:
                   - context: the reason for calling the function. this should be quoted string literal value.
                   - dag_order: functions have the same dag-order if they could be executed in parallel otherwise they have a higher g-order. Please add a code comment above this attribute to explain the order and dependencies.
                   - confidence: (in choosing this function).
                   - args: the name of the function args and the value in the execution graph. for example an arg value in a graph could be a literal or a graph variable $name_of_function.output  
                   - example_function_call_args: in addition to adding the function call args, provide *literal* example mapping for each arg. these literal examples should help you think about the variables you are passing around and if the inputs should be long-form text or structured primitives or object types 
                4. Add your "attention comments" to the top of the generated {VIZ} graph output listing the things you attended to as bullet points.
                  - the key step to attend to is how to chain args for the right functions together in step 3 while gathering as much data as possible.
                  - You must think about what types of inputs and outputs you are dealing with and use variables correctly as you pass variables from earlier steps to later steps. For example its not likely that you will pass literals to functions at later stages.
                  - remember to add all the steps and attention comments in a single {VIZ} output
          
                """
    # CHAT GPT re write of the same thing which strips off the fat
    #     PLAN = f"""
    # As a function and planning agent, follow these steps:
    # 1. Think about the question and use the 'function search' function to find available functions that will help find a good answer.
    # 2. Rate each function from 0 to 100 and provide a brief explanation for each rating. Prioritize functions with general output capabilities.
    # 3. Create a {VIZ} graph representing a nested chain of individual functions. Include the following for each function call:
    #    - `function_name`
    #    - `context` (a quoted string literal explaining the reason for the function call)
    #    - `dag_order` (determining the execution order and dependencies)
    #    - `confidence` (in selecting the function)
    #    - `args` (name and value in the execution graph, e.g., $name_of_function.output)
    #    - `example_function_call_args` (provide literal examples for function call arguments)
    # 4. Include "attention comments" (i.e. things you are attending to) throughout the {VIZ} graph output as you addressing key considerations:
    #    - Ensure correct chaining of arguments in step 3 while gathering data.
    #    - Use variables appropriately as inputs and outputs, avoiding passing literals in later stages if they are determined from the results of earlier stages."""

    USER_HINT = "Please return to me the graph representation (in the correct format) about the plan with respect to the question asked. "

    """
    learning
    
       Q: Where would you take people like  Snow White and Sinbad for dinner if they were not able to find a recipe that they liked to cook at home
       R : Reasoning here is the agent things they already know they cannot find a recipe but we as humans might try to first convince them by looking up recipe
       
      -  We may thing that examples like example1.output are interpreted as <token>.output but actually they are not (at time of writing). This is interesting.
      - it seems steps are useful but at the cost of context window. sometimes it does not finish the question because there is too much context. think about to use this
      - things that can go wrong
        - the outputs of later steps should not be literals generally. but they can be . watch for the not-using-outputs case - they should not try to treat outputs as structured (we could trim this ourselves)
        - examples should show the thought process e.g. if long form text is used or not but the LLM will hav more context with Function Defs at run time so might be early to worry
        - note its fine to have variables inside strings e.g. search "somethings somethings $var $var something"
        - 
    """
    ###################
    #  interesting example plans - we can use this to provide the schema in future when we settle on one
    #  in future we will audit these in RAG
    ###
    """
   
    
    interesting for its nested dag structure - observe ordinals in sub dags

    # Comment Section:
    # Initially, 'get_information_on_fairy_tale_characters' function has been called to understand the preferences of Snow White and Sinbad.
    # Their preferences have been used to search for a high rated recipe if that fails, restaurants have been searched using 'get_restaurant_reviews' and 'get_restaurant_reviews_other'.
    # The last two functions are executed parallely.

    dag:
        get_fairy_tale_characters_info:
            function: get_information_on_fairy_tale_characters # Get the preferences of given characters
            context: "Get Snow White's and Sinbad's favourite food type"
            dag-order: 1 # This will be the first function to execute
            confidence: 80 # High confidence as this is directly related to our characters
            args:
                question: $question.input
            example_function_call_args:
                question: "What food do Snow White and Sinbad like?"

        get_recipes_with_ratings:
            function: get_recipes_with_ratings # Get recipes based on the preference
            context: "Find highly rated recipes based on characters' preference"
            dag-order: 2 # Second function to execute. This function will use output from 'get_fairy_tale_characters_info' function
            confidence: 80 # High confidence in this function as it gives recipes with ratings
            args:
                what_to_cook: $get_fairy_tale_characters_info.output.likes
            example_function_call_args:
                what_to_cook: "Apples"
            fallback:
                dag:
                get_restaurant_reviews:
                    function: get_restaurant_reviews # If cooking fails, find restaurants
                    context: "Find restaurants suitable for characters' preferences"
                    dag-order: 1 # First in case the fallback is lead
                    confidence: 70 # Moderate confidence as it gives restaurants according to preference
                    args:
                        name_or_type_of_place: $get_fairy_tale_characters_info.output.likes
                    example_function_call_args:
                        name_or_type_of_place: "Apple Pie"

                get_restaurant_reviews_other:
                    function: get_restaurant_reviews_other # If cooking fails, find restaurants
                    context: "Find other restaurants suitable for characters' preferences"
                    dag-order: 1 # First in case the fallback is lead. It is executed in parallel with 'get_restaurant_reviews'
                    confidence: 70 # Moderate confidence as it gives restaurants according to preference
                    args:
                        name_or_type_of_place: $get_fairy_tale_characters_info.output.likes
                    example_function_call_args:
                        name_or_type_of_place: "Apple Pie"
    """

    ####

    """
    # Attention comments:
- First, obtain Snow White and Sinbad's favourite type of food.
- Use their preferred type of food to look for high-rated home-cooking recipes. 
- If no suitable recipe is found or our guests do not prefer home-cooking, looking up restaurant recommendations will be the next step. 

```yaml
# 1. get information on Snow White and Sinbad's favourite type of food
- function_name: get_persons_favourite_thing_of_type
  context: "To get Snow White and Sinbad's favourite type of food.",
  dag_order: 1
  confidence: 90
  args: 
    person: Snow White
    thing_type: food
  example_function_call_args: {person: "Snow White", thing_type: "food"} 

- function_name: get_persons_favourite_thing_of_type
  context: "To get Snow White and Sinbad's favourite type of food.",
  dag_order: 1
  confidence: 90
  args: 
    person: Sinbad
    thing_type: food
  example_function_call_args: {person: "Sinbad", thing_type: "food"} 

# 2. search for high-rated recipes according to their favourite food
- function_name: get_recipes_with_ratings
  context: "To find high-rated recipes based on favourite type of food.",
  dag_order: 2
  confidence: 100
  args: 
    what_to_cook: $get_persons_favourite_thing_of_type.output
    min_rating: 4.5
  example_function_call_args: {what_to_cook: "apple pie", min_rating: 4.5}

# 3. get restaurants recommendation if the homemade recipe search does not return a suitable result
- function_name: get_restaurant_reviews
  context: "To find restaurants based on favourite type of food if no suitable home-cooking recipe is found."
  dag_order: 3
  confidence: 90
  args: 
    name_or_type_of_place_preferred: $get_persons_favourite_thing_of_type.output
  example_function_call_args: {name_or_type_of_place_preferred: "Italian"} 

- function_name: get_restaurant_reviews_other
  context: "Run in parallel with get_restaurant_reviews to fetch restaurant details faster."
  dag_order: 3
  confidence: 85
  args: 
    name_or_type_of_place_preferred: $get_persons_favourite_thing_of_type.output
  example_function_call_args: {name_or_type_of_place_preferred: "Italian"} 
```

The `dag_order` allows us to know which functions can be run in parallel. Functions `get_persons_favourite_thing_of_type` can be run in parallel since they do not depend on each other. The same goes for `get_restaurant_reviews` and `get_restaurant_reviews_other`. 

The `args` field in each function call specifies the input for the function. It can be the literal value or the output of previous function calls. For example, `get_recipes_with_ratings` and `get_restaurant_reviews` take the output of `get_persons_favourite_thing_of_type` as input.

We need to think through what types of inputs and outputs each function needs or provides, and connect functions together in a suitable way. For instance, the output of `get_persons_favourite_thing_of_type` is used as the input of `get_recipes_with_ratings` and `get_restaurant_reviews`. Thus, even if the literal examples might not directly feed into the later functions, they're used to demonstrate the flow of information in the system.
    
    """
