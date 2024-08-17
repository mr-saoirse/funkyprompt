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
                """if the field type is a dict 
                - otherwise we extract nodes and edges in a different way"""
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
        


       
        