class CypherHelper:
    """
    see [age docs](https://age.apache.org/age-manual/master/intro/overview.html)
    """

    def __init__(self, model, db=None):
        """"""
        from funkyprompt.core import AbstractEntity

        self.model: AbstractEntity = model

    def query_from_natural_language(cls, question: str):
        """"""
        return None

    def get_graph_model_attributes(self, node):
        """the default node behviour is to just keep the name but we can 'index' other attributes
        this can either be done upfront or later on some trigger or job
        """
        return None

    # def upsert_path_query(self, node):https://age.apache.org/age-manual/master/clauses/create.html

    def create_script(self):
        """create the node - may well be a no-op but we register anyway"""
        label = self.model.get_model_fullname().replace(".", "_")
        q = f"""
        """
        return None

    def upsert_node_query(self, nodes):
        """
        create a node upsert query - any attributes can be upserted
        but labeled nodes are supposed to be unique by name
        """

        if not isinstance(nodes, list):
            nodes = [nodes]

        label = self.model.get_model_fullname().replace(".", "_")

        cypher_queries = []

        for n in nodes:
            """we may set some attributes like descriptions and stuff"""
            set_attributes = ""
            graph_attributes = self.get_graph_model_attributes(self.model)
            if graph_attributes:
                set_attributes = f"""SET n = {{
                        description: 'new desc'
                    }}"""

            cypher_queries.append(
                f"""MERGE (n:{label} {{name: '{n.name}'}})
                {set_attributes}
                RETURN n"""
            )

        """for now block them up but we investigate a more efficient notation
           we generally expect low cardinality upserts for entity types in practice
        """
        return "\n".join(cypher_queries)
