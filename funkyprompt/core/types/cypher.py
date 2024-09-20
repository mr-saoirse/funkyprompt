"""implement some basic batch merge statements - they generally take the conventional forms

MERGE (a:Type{name:x})-[e:Type({name:y}]-(b:Type{name:y})], SET a.property = 'value'
where each variable a,e,b is indexed in the batch e.g. a0, a1, a2...

funkyprompt uses a very simple type of graph since its hybrid
we are simply registering keys and relationships between them 
so we dont write a lot of properties in the graph except for system props

The type system works with the AbstractEntity to qualify node and edge types

This helps agents find things it would otherwise lose

"""

import typing



class CypherHelper:
    """
    see [age docs](https://age.apache.org/age-manual/master/intro/overview.html)
    """

    def __init__(self, model, db=None):
        """"""
        from funkyprompt.core import AbstractEntity

        self.model: AbstractEntity = model
        
    @classmethod
    def query_path_n_from_node(cls, entity, n=1):
        """
        get a full set of paths of distance n from the node
        """
        label = entity.get_model_fullname().replace(".", "_")
        Q = f"""MATCH p=(n:{label} {{name: '{entity.name}'}})-[*{n}]->(m)
	             RETURN p"""

    def query_from_natural_language(cls, question: str):
        """"""
        return None

    def get_graph_model_attribute_setter(self, node, has_full_entity:bool=False, alias='n'):
        """the default node behviour is to just keep the name but we can 'index' other attributes
        this can either be done upfront or later on some trigger or job
        """
        #this is a marker that shows we have associated a full entity with the node
        attributes = f"{alias}.entity = 1" if has_full_entity else None
        
        if attributes:
            return f"""SET {attributes}"""
        return ''

    # def upsert_path_query(self, node):https://age.apache.org/age-manual/master/clauses/create.html

    def create_script(self):
        """create the node - may well be a no-op but we register anyway"""
        label = self.model.get_model_fullname().replace(".", "_")
        q = f"""
        """
        return None
    
    def upsert_relationship_query(self, relationships):
        """
        the entities may contain relationships or may not
        """
        return None
    
    def upsert_nodes_statement(self, nodes, label:str=None, has_full_entity:bool=False):
        """
        create a node upsert query - any attributes can be upserted
        but labeled nodes are supposed to be unique by name
        
        Args:
            nodes: a list of entities 
            label: its assumed the label is based on the model but can be anything
            has_full_entity: a tracker to see if we are also adding the entity or just making a relationship to a node 
        """

        if not isinstance(nodes, list):
            nodes = [nodes]

        label = label or self.model.get_model_fullname().replace(".", "_")
        
        cypher_queries = []

        i = 0
        for i,n in enumerate(nodes):
            """any nodes can be added for any time but often we do a batch based on the source model
            see Edge and Node types to understand the interface for getting node_type
            """
            applied_label = getattr(n, 'node_type', label).replace('.','_')
            """we may set some attributes like descriptions and stuff"""
            cypher_queries.append(
                f"""MERGE (n{i}:{applied_label} {{name: '{n.name}'}})
                { self.get_graph_model_attribute_setter(n, alias=f"n{i}", has_full_entity=has_full_entity)  }
               """
            )

        """for now block them up but we investigate a more efficient notation
           we generally expect low cardinality upserts for entity types in practice
        """
        if cypher_queries:
            """fetch a sample"""
            return "\n".join(cypher_queries) + f" RETURN n{i}"

    def upsert_edges_statement(self, edges):
        """
        create a batch upsert that returns the last one sample
        """
        if edges:
           return "\n".join([e.make_edge_upsert_query_fragment(index=i) for i, e in enumerate(edges)]) + f" RETURN e{len(edges)-1}"
       
    def upsert_path_statements(self, entities, path_node:str="Resource"):
        """
        The template for this is below, and we need it to batch, ensure no duplicate edges on paths
                
        
        MERGE (a:NodeLabel {name: "NodeA"})
        MERGE (b:NodeLabel {name: "NodeB"})
        MERGE (c:NodeLabel {name: "NodeC"})
        MERGE (a)-[:REL_TYPE]->(b)  
        MERGE (b)-[:REL_TYPE]->(c)

        """
        
        from funkyprompt.core.AbstractModel import Node, Edge
        from funkyprompt.core import AbstractEntity
        from funkyprompt.core.fields.annotations import AnnotationHelper
        
        """conventional experiment to add paths a/b/c/d"""
        gpaths = []
        for e  in entities:
            #a = AnnotationHelper(e)
            paths = getattr(e,'graph_paths', [])
            if paths:
                for value in paths:
                    parts = value.split('/')
                    if len(parts) == 1:
                        parts.append('NONE')
                    label = e.get_model_fullname().replace(".", "_")
                    i = len(gpaths)
                    template = f"""MERGE (a{i}:{label} {{name: "{e.name}"}})
                    MERGE (b{i}{{name: "{parts[0]}"}})
                    MERGE (c{i}{{name: "{parts[1]}"}})
                    MERGE (a{i})-[:TAG]->(b{i})  
                    MERGE (b{i})-[:TAG]->(c{i})
                    """
                    gpaths.append(template)
                    
        return "\n".join(gpaths)
            
    def distinct_edges(self, entities: typing.List[typing.Any]):
        """
        uses the model annotation conventions to extract nodes related to item.
        fields should be annotated with `RelationshipField` 
        and then we can either have anonymous edges as dicts or lists of AbstractEntity
        """
        from funkyprompt.core.AbstractModel import Node, Edge
        from funkyprompt.core import AbstractEntity
        from funkyprompt.core.fields.annotations import AnnotationHelper
  
        if not entities:
            return []
              
        if not isinstance(entities, list):
            entities: typing.List[AbstractEntity] = [entities]
        items = []
        for e in entities:
            a = AnnotationHelper(e)
                                    
            for field_name, edge_type in a.typed_edges.items():
                edge_type = edge_type or f"HAS_{field_name.upper()}" #f"HAS_{t.get_model_name().upper()}"
                """assume relationships are dicts for now"""
                field = getattr(e, field_name, None) or {}
             
                """if the field type is a dict """
                if isinstance(field, dict):
                    for target_name, description in field.items():
                        items.append(
                            Edge(source_node=Node(name=e.name,node_type=e.get_model_fullname() ),
                                #we dont know the target node type yet
                                target_node=Node(name=target_name),
                                #this is the edge description
                                description=description,
                                type=edge_type))
                #the case that is based on the typed child entities that have relations - strings are treated like generic backlinks or resources
                elif isinstance(field, str) or isinstance(field, list) or isinstance(field, AbstractEntity):
                    if not isinstance(field,list):
                        field: typing.List[AbstractEntity] = [field]
                    """now we have a collection of abstract 'child' entities that can be added as typed relationships
                       These will have the form HAS_TYPE -> TARGET_TYPE(name)
                    """
                    for t in field:
                        if isinstance(e, AbstractEntity):
                            items.append(
                                Edge(source_node=Node(name=e.name,node_type=e.get_model_fullname() ),
                                     target_node=Node(name=t.name, node_type=t.get_model_fullname()),
                                     type=edge_type))
                        #string table are just labels or back links
                        if isinstance(e,str):
                            items.append(
                                Edge(source_node=Node(name=e,node_type='public.resource' ),
                                     target_node=Node(name=t.name, node_type=t.get_model_fullname()),
                                     type=edge_type))
                #a third type would be a tuple instead of a dict to describe the agent - we could add this thing to the runner
        return items

    # def upsert_typed_paths_queries(self, entities, ntype:str= 'Topic'):
    #     """add paths directly in batch - hard coded to a certain typ paths for now and its of degree two but we can do more general things if useful
    #        these are Topic paths for the users interests
    #     """
    #     paths = []
    #     for e in entities:
    #         if hasattr(e,'graph_paths'):
    #             ps = set()
    #             for p in e.graph_paths:
    #                 ps |= {p}
    #             for i, p in enumerate(ps):            
    #                 label = e.get_model_fullname().replace(".", "_")
    #                 parts = p.split('/')
    #                 p = f"""CREATE p{i} = (n{i}:{label} {{name:'{e.name}'}})-[:HAS]->(m{i}:{ntype} {{name:'{parts[0]}'}})-[:HAS]->(o{i}:{ntype} {{name:'{parts[1]}'}})"""
    #                 paths.append(p)  
    #         return "\n".join(paths)
    
        
    def upsert_relationships_queries(self, entities):
        """
        relationships register nodes that do not exist and add relationships between the source and target nodes
        this is how we create graph bottoms and its ok for them to be not fully connected
        """
        
        from funkyprompt.core.AbstractModel import Edge
            
        """extract the nodes and the edges from the entities"""
        
        edges: typing.List[Edge] = self.distinct_edges(entities)
        """get distinct nodes used in the relationships"""
        new_nodes = list({e.target_node.key : e.target_node for e in edges}.values())        
        edges_query = self.upsert_edges_statement(edges)
        node_query = self.upsert_nodes_statement(new_nodes)
        
        """return both queries for execution"""
        return node_query,edges_query
        


       
        
        

class _GraphStatistics:
    """some helpers (WIP) - most of these are aspirational from neo4j that wed like to support"""
    @staticmethod
    def node_count():
        return """MATCH (n)
            RETURN count(n) AS total_nodes"""

    @staticmethod
    def nodes_by_label():
        return """MATCH (n)
RETURN labels(n) AS node_labels, count(n) AS total_by_label
ORDER BY total_by_label DESC"""

    @staticmethod
    def node_degree():
        return """MATCH (n)
RETURN n.name, size((n)--()) AS degree
ORDER BY degree DESC"""

    @staticmethod
    def average_node_degree():
        return """MATCH (n)
RETURN avg(size((n)--())) AS average_degree"""
            
    @staticmethod
    def max_degree():
        """MATCH (n)
RETURN max(size((n)--())) AS max_degree """

    @staticmethod
    def min_degree():
        """MATCH (n)
RETURN  min(size((n)--())) AS min_degree"""

    @staticmethod
    def degree_distribution():
        return """MATCH (n)
WITH size((n)--()) AS degree
RETURN degree, count(*) AS count
ORDER BY degree DESC"""

    @staticmethod
    def node_label_statistics():
        return """MATCH (n)
WITH labels(n) AS node_labels, size((n)--()) AS degree
RETURN node_labels, count(n) AS total_nodes, avg(degree) AS avg_degree, max(degree) AS max_degree, min(degree) AS min_degree
ORDER BY total_nodes DESC"""

    @staticmethod
    def relationships_count():
        return """MATCH ()-[r]->()
RETURN count(r) AS total_relationships"""

    @staticmethod
    def relationship_count_by_type():
        return """MATCH ()-[r]->()
RETURN type(r) AS relationship_type, count(r) AS total_by_type"""

    @staticmethod
    def avg_inter_node_path_length():
        return """MATCH (n), (m)
WHERE id(n) < id(m)  
WITH n, m
MATCH p=shortestPath((n)-[*]-(m))   
RETURN avg(length(p)) AS avg_path_length"""

    @staticmethod
    def graph_density():
        return """MATCH (n), (m)
WITH count(n) AS num_nodes, count((n)-[r]->(m)) AS num_edges
RETURN (2.0 * num_edges) / (num_nodes * (num_nodes - 1)) AS graph_density;"""

    @staticmethod
    def triangle_count(edge: str = 'TAG'):
        return f"""MATCH (a)-[:{edge}]-(b), (b)-[:{edge}]-(c), (c)-[:{edge}]-(a)
WITH a, b, c
RETURN count(DISTINCT [a, b, c]) / 3 AS triangle_count;"""

    @staticmethod
    def closeness_centrality():
        return """-- Initialize closeness centrality
MATCH (n)
SET n.closeness_centrality = 0;

-- Calculate closeness centrality
MATCH (n), (m), p = shortestPath((n)-[*]-(m))
WITH n, sum(length(p)) AS total_path_length
SET n.closeness_centrality = 1.0 / total_path_length
RETURN n.id, n.closeness_centrality
ORDER BY n.closeness_centrality DESC;"""


    @staticmethod
    def degree_centrality():
        return """MATCH (n)
SET n.degree_centrality = size((n)--())
RETURN n.id, n.degree_centrality
ORDER BY n.degree_centrality DESC;"""

    @staticmethod
    def between_node_centrality():
        return """-- Initialize betweenness centrality for all nodes
MATCH (n)
SET n.betweenness_centrality = 0;

-- Find shortest paths and update betweenness centrality
MATCH (source), (target), p = shortestPath((source)-[*]-(target))
WITH nodes(p) AS path_nodes
UNWIND path_nodes AS n
SET n.betweenness_centrality = n.betweenness_centrality + 1
RETURN n.id, n.betweenness_centrality
ORDER BY n.betweenness_centrality DESC;"""

    @staticmethod
    def page_rank():
        return """-- Create an index for performance
CREATE INDEX ON graph_vertices(id);

-- Initialize the PageRank score for all nodes
MATCH (n) 
SET n.pagerank = 1.0;

-- Run the PageRank algorithm iteratively
WITH 0.85 AS damping_factor, 0.15 AS reset_value
MATCH (n)-[r]->(m)
WITH n, m, count(r) AS num_outgoing_links
SET m.pagerank = reset_value + damping_factor * sum(n.pagerank / num_outgoing_links)
RETURN m.id, m.pagerank
ORDER BY m.pagerank DESC;"""