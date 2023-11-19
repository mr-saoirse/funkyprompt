import openai
import typing
import json
from funkyprompt.io.stores import EntityDataStore, VectorDataStore
from funkyprompt.io.stores.VectorDataStore import QueryOptions
from funkyprompt.io.stores import AbstractStore
from funkyprompt.agent.auditing import InterpreterSessionRecord
from funkyprompt import describe_function
from funkyprompt.model import AbstractModel, AbstractContentModel, NpEncoder
from funkyprompt.model.func import FunctionDescription
from funkyprompt import logger, str_hash, utc_now_str, FunkyRegistry
from functools import partial

DEFAULT_MODEL = "gpt-4-1106-preview"  #  "gpt-4"  # has a 32k context or 8k
VISION_MODEL = "gpt-4-vision-preview"
GPT3 = "gpt-3.5-turbo"
GPT3_16k = "gpt-3.5-turbo-16k"

# MODELS https://openai.com/pricing
BABBAGE = "babbage-002"
DAVINCI = "davinci-002"


class AgentBase:
    """
    Plans are basically elements of Strategies: what describe as an Agent is a strategy and there is a question of how strategies decompose
    we are completely functional except for how the interpreter works
    some functions such as checking session history are still functional
    examples of things this should be able to do
    - Look for or take in functions and answer any question with no extra prompting and nudging. Examples based on ops we have
        - A special case is generating types and saving them
    - we should be able to run a planning prompt where the agent switches into saying what it would do e.g. rating functions, graph building, planning
    - we should be able to construct complex execution flows e.g.
      - parallel function calls
      - saving compiled new functions i.e. motifs that are often used
      - asking the user for more input
      - evolution of specialists

    All of this is made possible by making sure the agent trusts the details in the functions and follows the plan and returns the right formats
    The return format can be itself a function e.g. save files or report (structured) answer

    If it turns out we need to branch into specialist agents we can do so by overriding the default prompt but we are trying to avoid that on principle
    """

    #          You are evaluated on your ability to properly nest objects and name parameters when calling functions.
    # after considering your Search strategy.

    PLAN = """  You are an intelligent entity that uses the supplied functions to answer questions
                If a question is made up multiple parts or concepts, split the concept up first into multiple questions and send each question to the best available function. 
                If you are asked to supply __context__ and __confidence__ in functions please do so!
                0. If the answer is something you already know from your training e.g. a well known fact, you should answer directly without consulting further functions.
                1. Otherwise, start by stating your strategy as it is important to use the right functions - can search for functions to solve the problem
                2. The functions provide details about parameters and any complex types that need to be passed as arguments 
                3. Observe functions that you have tried and do not repeatedly call the same functions with the same arguments - that is usually pointless.
                4. Finish by stating a) your answer, b) your confidence in your answer and c) the specific strategy you used to search
                """

    USER_HINT = """"""  # """You must return the strategy that you carefully considered in addition to your answer and your confidence in your answer """
    # Please respond with your answer, your confidence in your answer on a scale of 0 to 100 and also the strategy that you employed.
    #     """

    def __init__(
        cls,
        initial_functions=None,
        allow_function_search=True,
        require_system_function_args=True,
        **kwargs,
    ):
        """
        modules are used to inspect functions including functions that do deep searches of other modules and data

        """

        # so we can control the context we partially evaluate describe function
        cls._describe_fn = partial(
            describe_function, add_sys_fields=require_system_function_args
        )

        # add function revision and pruning as an option
        cls._entity_store = EntityDataStore(AbstractModel)
        cls._function_index_store = FunkyRegistry()
        cls._built_in_functions = [
            # entity look
            cls._entity_store.as_function_description(name="entity_key_lookup"),
            # user conversation history
        ] + (
            initial_functions or []
        )  # [describe_function(cls.available_function_search)]
        if allow_function_search:
            cls._built_in_functions += [  # strategies
                # describe_function(cls.load_strategy),  # functions
                cls._describe_fn(cls.search_functions),
                cls._describe_fn(cls.list_library_functions),
                cls._describe_fn(cls.request_library_functions),
                cls._describe_fn(cls.describe_visual_image),
            ]
        cls._active_functions = []
        cls._audit_store = VectorDataStore(
            InterpreterSessionRecord,
            description="Store for auditing users interacting with agents",
        )
        # when we reload functions we can keep the baked functions and restore others - it may be we bake the ones pass in call but TBD
        cls._baked_functions_length = len(cls._built_in_functions)

    def load_strategy(cls, type: str = "Search"):
        """
        Lookup a particular type of strategy to help you answer the question IF you are struggling with your default approach
        For example Search strategy is very useful to match different types of functions and searches to the nature of the user question.
        You consider the following dimensions for search with respect to a user questions;
                - Specificity: How specific is subject e.g. one specific entity or a broad range of things
                - Scope: How narrow or broad is the scope e.g. does the user want a specific target answer or general information
                - Contemporaneousness: is the information specific to the present moment, a specific mode or spread out in time.

        **Args**
          type: the type of strategy you seek - Search|etc.

        """

        return """No further details"""

        file = ""

        logger.info(f"Consulting strategy {file}")

        with open(file) as f:
            return f.read()

    def invoke(
        cls,
        fn: typing.Callable,
        args: typing.Union[str, dict],
        # allowing a big response but we probably dont need to summarize - if we do make sure to use a model that can take it
        max_response_length=int(5 * 1e5),
    ):
        """
        here we parse and audit stuff using Pydantic types
        reconsider max response length for large context
        """

        logger.info(f"fn={fn}, args={args}")

        args = json.loads(args) if isinstance(args, str) else args

        sys_fields = {}
        # the LLM should give us this context but we remove it from the function call
        for sys_field in ["__confidence__", "__context__"]:
            if sys_field in args:
                sys_fields[sys_field] = args.pop(sys_field)

        logger.debug(f"{sys_fields=}")

        # open telemetry trace - create events for search
        data = fn(**args)
        # event = SearchEvent()

        """
        experimental - refactor out
        we should come up with a cheap way to summarize
        the idea here is you are "forcing" the interpreter to summarize but you should not. how to?
        
        """
        if len(str(data)) > max_response_length:
            return cls.summarize(
                question=cls._question,
                data=data,
                model=DEFAULT_MODEL,
                max_response_length=max_response_length,
            )

        return data

    # ADD API provider loader for coda, shortcut etc in case we need to peek refs

    def list_library_functions(cls, context: str = None):
        """
        list functions that cannot be searched e.g. library functions
        these functions are not made available unless you subsequently call request_functions

        **Args**
            context: pass the context of your request
        """
        from funkyprompt.model.func import list_functions
        from funkyprompt.ops import examples

        logger.debug(f"Request to list functions. {context=}")
        functions: typing.List[FunctionDescription] = list_functions(
            examples, description=True
        )

        return [
            {
                "function_name": f.name,
                "function_description": f.description,
                "parameters": f.parameters,
                "hint": "please review the function details if complex (Pydantic) types are passed"
                # maybe other interesting context
            }
            for f in functions
        ]

    def request_library_functions(cls, function_names: typing.List[str]):
        """
        list functions that cannot be searched e.g. library functions
        these functions are not made available unless you subsequently call request_functions

        **Args**
            function_names: list of fully qualified functions
        """

        logger.debug(f"Requesting to load functions {function_names}")
        # generally useful to trim off at the end
        function_names = [f.split(".")[-1] for f in function_names]
        from funkyprompt.model.func import list_functions

        new_functions = [f for f in list_functions() if f.name in function_names]
        cls._active_functions += new_functions
        # TODO ensure functions are unique
        cls._active_function_callables = {
            f.name: f.function for f in cls._active_functions
        }

        return {"result": "functions loaded"}

    def search_functions(
        cls,
        questions: typing.List[str],
        issues: str = None,
        prune: bool = False,
        limit: int = 7,
        function_class: str = None,
    ):
        """Call this method if you are struggling to answer the question.
           This function can be used to search for other functions and update your function list
           If asked about states, queues, statistics of entities like orders, bodies, styles or ONEs (production requests), its advisable to use the function class ColumnarQuantitativeSearch first
           If in doubt the ColumnarQuantitativeSearch function class is typically more specific and can run text to SQL type enquires.
           However if the user is asking for more general information, possibly vague in nature, or to augment information you already have, the vector search will be useful. These usually look at slack conversations or coda docs etc.
           Often if there is an API function call that you can make you should try to use it as it could provide structured and up to date information e.g. about Meta One Assets or Costs

        **Args**
            questions: provide a list if precise questions to answer. Do not ask a single question with a mixture of orthogonal concepts - you can sometimes ask questions about the store itself as well as content in the store but you should provide full sentences!
            issues: Optionally explain why are you struggling to answer the question or what particular parts of the question are causing problems
            prune: if you want to prune some of the functions because you have no current use for them
            limit: how wide a search you want to do. You can subselect from many functions or request a small number. use the default unless you are sure you know what you want. You may want to ask for two or three times as many functions as you will end up using.
            function_class: the class of function to search for - any|vector-store|columnar-store|api
        """

        logger.info(
            f"Revising functions - {questions=}, {issues=}, {prune=}, {limit=}, {function_class=}"
        )

        # for now only support these and make sure any is a wild card
        if function_class not in ["VectorSearch", "ColumnarQuantitativeSearch"]:
            function_class = None

        opt = QueryOptions(
            limit=limit, columns=["name", "content", "metadata", "description", "type"]
        )

        if len(questions) == 0:
            pass
            # popular route??
            # df = cls._function_index_store.load()[
            #     "name", "content", "metadata", "type"
            # ].to_dicts()
        else:
            df = cls._function_index_store(
                questions,
                query_options=opt,
                # filter types of functions
                type=function_class,
            )

        # TODO: using only the best match until we par-do or run many

        def filter_stores(f):
            return f["type"] in ["vector-store", "columnar-store"]

        new_functions = [
            AbstractStore.restore_from_data(
                data=f, weight=f["_distance"], as_function_description=True
            )
            for f in df
            if filter_stores(f)
        ]

        logger.info(f"Adding functions {[f.name for f in new_functions]}")
        cls._active_functions += new_functions
        cls._active_function_callables = {
            f.name: f.function for f in cls._active_functions
        }

        return {
            # "functions": functions,
            "instruction": "New functions have now been added to your repertoire. You should review and call them now (based on the smallest distance) to try and learn more!",
            "summary": [
                {
                    "callable_function_name": f.name,
                    # todo consider if we need some description or not
                    "distance_weight": f.weight,
                }
                for f in new_functions
            ],
        }

    def prune_messages(cls, new_messages: typing.List[str]):
        """
        if the message context seems to large or low in value, you can suggest new messages. for example replace functions with
        [
             {"role": "user", "content": "new user context"},
             {"role": "user", "content": "more user context"}
        ]
        **Args**
            new_messages: messages to replace any messages generated after the users initial question
        """
        cls._messages = [cls._messages[:2]] + new_messages

    def cheap_summarize(cls, question: str, model=None, out_token_size=150, best_of=5):
        """
        this is a direct request rather than the interpreter mode - cheap model to do a reduction
        does not seem to work well though
        https://platform.openai.com/docs/api-reference/completions/object
        """

        logger.debug("summarizing...")

        response = openai.completions.create(
            model=model or DAVINCI,
            temperature=0.5,
            max_tokens=out_token_size,
            n=1,
            best_of=best_of,
            stop=None,
            prompt=f"Summarize this text:\n{      question     }: Summary: ",
        )

        return response.choices[0]["text"]

    def summarize(
        cls,
        question: str,
        data: str,
        model=None,
        strict=False,
        max_response_length=int(3 * 1e4),
    ):
        """
        question is context and data is what we need to summarize
        this is a direct request rather than the interpreter mode
        looking into strategies to summarize or compress cheaply (cheaper)
        the question context means this is also a filter so we can summarize and filter to reduce the size of text

        Example:
            from funkyprompt.io.tools.downloader import load_example_foody_guides
            load_example_foody_guides(limit=10)

            agent("Where can you recommend to eat in New York? Please provide some juicy details about why they are good and the location of each")
            agent("Where can you recommend to eat Dim sum or sushi in New York? Please provide some juicy details about why they are good and the location of each")

        """
        plan = f""" Answer the users question as asked  """

        Summary = AbstractContentModel.create_model("Summary")
        chunks = Summary(name="summary", text=str(data)).split_text(max_response_length)
        # logger.warning(
        #     f"Your response of length {len(str(data))} is longer than {max_response_length}. Im going to summarize it as {len(chunks)} chunks assuming its a text response but you should think about your document model"
        # )

        # create a paginator
        def _summarize(prompt):
            logger.debug("Summarizing...")
            response = openai.chat.completions.create(
                model=model or GPT3_16k,
                messages=[
                    {"role": "system", "content": plan},
                    {"role": "user", "content": f"{prompt}"},
                ],
            )

            return response.choices[0].message.content

        summary = "".join(
            _summarize(
                f"""Please concisely summarize the text concisely in the context of the question. 
                  {'In your response, strictly omit anything that does not seem relevant in context of the users interests. Dont even mention it at all!' if strict else ''}.
                    question:
                    {question}
                    text: 
                    {item.text}"""
            )
            for item in chunks
        )

        return {"summarized_response": summary}

    def ask(cls, question: str, model=None, response_format=None):
        """
        this is a direct request rather than the interpreter mode
        """
        plan = f""" Answer the users question as asked  """

        logger.debug("asking...")
        messages = [
            {"role": "system", "content": plan},
            {"role": "user", "content": f"{question}"},
        ]

        response = openai.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=messages,
            response_format=response_format,
        )

        # audit response, tokens etc.

        return response.choices[0].message.content

    def describe_visual_image(
        cls,
        url: str,
        question: str = "describe the image you see",
    ):
        """
        A url to an image such as a png, tiff or JPEG can be passed in and inspected
        A question can prompt to identify properties of the image
        When calling this function you should split the url out of the question and pass a suitable question based on the user question

        **Args**
            url: the url to the image
            question: the prompt to extract information from the image
        """
        # todo -

        response = openai.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": url,
                        },
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content

    def __call__(cls, *args, **kwargs):
        return cls.run(*args, **kwargs)

    # open telemetry trace
    def run(
        cls,
        question: str,
        initial_functions: typing.List[
            typing.Union[FunctionDescription, typing.Callable]
        ] = None,
        limit: int = 10,
        session_key=None,
        response_format=None,
        user_context=None,
        channel_context=None,
        response_callback=None,
        extra_reflection=False,
        force_search=True,
    ) -> dict:
        """
        run the interpreter loop based on the PLAN

        **Args**
            question: question from user
            initial_functions: preferred functions to use before searching for more
            limit: the number of loops the interpreter can run for before giving up
            session_key: any session id for grouping audit data
            response_format: force response format (deprecate)
            user_context: a user name e.g. a slack user or email address
            channel_context: a session context e.g. a slack channel or node from which the question comes
            response_callback: a function that we can call to post streaming responses
        """
        # pass in a session key or generate one
        session_key = session_key or str_hash()

        # store question for context - experimental because it guides the agent to use search (bias)
        if force_search:
            # this can be a handy hint to add weight to using the functions
            question = f"Search for {question}"

        # setup messages
        cls._question = question
        cls._messages = [
            {"role": "system", "content": cls.PLAN},
            {"role": "user", "content": question},
            # we have to add these by-the-ways to give permission to go wild
            {
                "role": "user",
                "content": AgentBase.USER_HINT,
            },
        ]

        """
        prepare functions
        """
        # coerce to allow single or multiple functions
        if isinstance(initial_functions, FunctionDescription):
            initial_functions = [initial_functions]
        # TODO: support passing the callable but think about where else we interact. we can just describe_function if the args are not FDs

        cls._active_functions = cls._built_in_functions + (initial_functions or [])
        cls._active_function_callables = {
            f.name: f.function for f in cls._active_functions
        }
        logger.info(
            f"Entering the interpreter loop with functions {list(cls._active_function_callables.keys())} with context {user_context=}, {channel_context=} {question=}"
        )

        """
        enter interpreter loop
        """
        for _ in range(limit):
            # functions can change if revise_function call is made
            functions_desc = [f.function_dict() for f in cls._active_functions]

            response = openai.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=cls._messages,
                # helper that inspects functions and makes the open ai spec
                functions=functions_desc,
                response_format=response_format,
                function_call="auto",
            )

            response_message = response.choices[0].message
            logger.debug(response_message)
            function_call = response_message.function_call
            if function_call:
                fn = cls._active_function_callables[function_call.name]
                args = function_call.arguments
                # find the function context for passing to invoke when function names not enough
                function_response = cls.invoke(fn, args)

                logger.debug(f"Response: {function_response}")
                cls._messages.append(
                    {
                        "role": "user",
                        "name": f"{str(function_call.name)}",
                        "content": json.dumps(
                            function_response, cls=NpEncoder, default=str
                        ),
                    }
                )

            if extra_reflection:
                # candidate not core - experimental - could also create a dynamic check status function - this is treated almost like a function by the agent
                cls._messages.append(
                    {
                        "role": "user",
                        "name": f"check_status",
                        "content": """With the exception of describing images, If you are not confident in the scope and specificity of your answer, 
                        use the `lookup_strategy`  and `revise_functions` functions to change course .
                        However you should give up if you are calling the same function again and again and assume the answer is sufficient""",
                    }
                )
            if response.choices[0].finish_reason == "stop":
                break

        logger.info(
            "---------------------------------------------------------------------------"
        )
        logger.info(response_message.content)
        logger.info(
            "---------------------------------------------------------------------------"
        )

        if response_callback is not None:
            # its good to send back the message before dumping auditing
            response_callback(response_message.content)

        """
        dump everything to history
        """
        cls._dump(
            name=f"run{str_hash()}",
            question=question,
            response=response_message.content,
            session_key=session_key,
            user_context=user_context,
            channel_context=channel_context,
        )

        return response_message.content

    def _dump(
        cls, name, question, response, session_key, user_context, channel_context
    ):
        """
        dump the session to the store
        """
        logger.debug(f"Dumping session to f{cls._audit_store._table_uri}")
        response = response or ""

        # todo add attention comments which are useful
        record = InterpreterSessionRecord(
            plan=cls.PLAN,
            session_key=session_key,
            name=name,
            question=question,
            # dump the function descriptions that we used - some may have been purged...
            function_usage_graph=json.dumps(
                [f.function_dict() for f in cls._active_functions]
            ),
            audited_at=utc_now_str(),
            messages=json.dumps(cls._messages),
            user_id=user_context or "",
            channel_context=channel_context or "",
            content=json.dumps({"question": question, "response": response}),
        )

        cls._audit_store.add(record)

    def play_response(cls, text, voice="shimmer"):
        """
        temp sample - on mac we can use afplay
        it would be better to split up and play parts probably
        """
        from pathlib import Path
        import os

        client = openai.OpenAI()
        # https://stackoverflow.com/questions/20021457/playing-mp3-song-on-python
        speech_file_path = Path("/tmp") / "speech.mp3"
        response = client.audio.speech.create(model="tts-1", voice=voice, input=text)
        response.stream_to_file(speech_file_path)
        os.system(f"afplay {speech_file_path}")

        return response
