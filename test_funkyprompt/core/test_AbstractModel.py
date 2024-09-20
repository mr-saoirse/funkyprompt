from funkyprompt.core import AbstractModel
def test_markdown_parse():
    """
    this markdown format may change. markdown should be a little flexible so we should use yaml or json for the more general model loading
    It is important to include a model name and description (core prompt) as well as structure response type(s) and api function calls
    
    the pydantic agents can load runtime functions from a library but in this case of external APIs it is assumed they require just a uri and some sort of factory or registration process external to the agent
    
    """
    
    markdown = f"""# CityFinder\n\nI want you to list out capital cities and countries for the continent the user\nasks about. 
    Anything else they ask about you can use functions or entity\nsearch\n\n
    ## Structured Response Types\n\n### CapitalCities\n\n**field name** | **description** | **type**  \n---|---|---  \nresult | list the capital cities and their country | List[dict]  \ncomments | any additional comments you have | str  \n  \n
    ## Available Functions\n\n#### get_stuff\n\nUse this to get the stuff. \n\n_https://www.mydomain.com/routers/endpoints_\n\n"""
    
    a = AbstractModel.create_model_from_markdown(markdown)
    
    assert a.get_model_name() == 'CityFinder', "Failed to parse agent name"
    assert len(a.Config.functions) == 1, "Failed to parse a single function"
    
    
