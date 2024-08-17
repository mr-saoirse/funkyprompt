
"""TODO

still fleshing out the approach for graph
key things are how we map from entity models to nodes and edges and then how we bulk upsert same efficiently
at the moment there are actually three blocks which is unnecessary inside the postgres services
- we add the primary node
- we add related nodes
- we add related edges 

This can easily be merged into a single statement the way we have done it

the general approach is to use attribute merges (a:Type{name:x})-[e:Type({name:y}]-(b:Type{name:y})]
"""
# p = PersonPreferences(name='test', related_entities={'test_alt_1': "some details about the thing",'test_alt_2': "some details about the thing" })
# p.cypher().distinct_edges(p)
# # TEST creating some nodes and edges and reading them back
# PersonPreferences(**entity_store(PersonPreferences).update_records(p)[0])
# #PersonPreferences._lookup_entity('test',include_relations=True)[0]