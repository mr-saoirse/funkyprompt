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
    
    


def test_construction_from_markdown_complex_types():
    """"""
    markdown =   """# Notes\nThe 'Notes' agent is designed to manage the ingestion of notes. It can derive entities and tags as `graph_paths` and save content with backlinks for graph paths. The agent can also visit web links to gather more information when necessary.\n\n## Structured Response Types\n### Note\n| Field Name   | Type                | Description                                      |\n|--------------|---------------------|--------------------------------------------------|\n| name         | str                 | The name of the note                             |\n| content      | str                 | A description of the note                        |\n| uri          | Optional[str]       | An optional web link for the note                |\n| image_uri    | Optional[str]       | An optional web link to an image or thumbnail    |\n| category     | Optional[str]       | A note category                                  |\n| rating       | float               | A rating score from 0 to 1                        |\n| graph_paths  | Optional[List[str]]           | A list of tags of the form T/C where T is a specific Tag and C is a broad category |\n\n## Available Functions\n- [get:/scrape/site](https://domain.com/prefix/docs#/Scrape/scrape_text_scrape_site_get) : This function is essential for visiting a web link to scrape text and gather more information for the notes."""
 
    from funkyprompt.core import AbstractContentModel

    """this type contains various python type annotations and we should test more"""
    Notes = AbstractContentModel.create_model_from_markdown(markdown)



def test_construction_from_markdown_pure_json_schema():
    """unlike the cases above where we take python annotations in the tables, we should test other dialects
       struct json schema fields could be represented but maybe less concisely and we could map those too
    
    """
    assert 1==1, "must be going crazy"