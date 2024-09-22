# from pydantic import Field

# class TestObject(AbstractModel):
#     """You are a simple agent that answers the users question with the help of functions. 
    
# Please respond in a structured format with fenced json. Using the response format provided"""
             
#     person: str = Field(description="A person that is of interest to the user")
#     color: str = Field(description="A color that the person likes")
#     object_of_color: str = Field(description="An object that is the color of the persons favorite color")
        
#     @classmethod
#     def favorite_color(cls, person:str):
#         """
#         For three people Bob, Henrik and Ursula, you can ask for the favorite color and get an answer 
        
#         Args:
#             person: the name of the person
#         """
        
#         return {
#             "bob": "green",
#             "henrik": "yellow",
#             "ursula": "red"
#         }.get(person.lower())
    
#     @classmethod
#     def objects_of_color(cls, color:str):
#         """
#         For a given color, get an object of this color
        
#         Args:
#             color: the color
#         """
        
#         return {
#             "green": "turtle",
#             "yellow": "cup",
#             "red": "car"
#         }.get(color.lower())
    
# agent = Runner(TestObject)
# #could ask `"What object has the color that henrik likes"`
# Markdown(agent("Tell me about henrik",
#       CallingContext(model='claude-3-5-sonnet-20240620')
#      ))