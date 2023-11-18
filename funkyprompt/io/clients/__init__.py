import re
from .duck import duckdb

# need to add lance client stuff to do this
# def query_stores(query):
#     """
#     Query over all stores - experimental
#     this is not a proper parser - we replace dataset queries with schema_table and it is not safe
#     with a little more work we could replace the tokens with a regex and then use aliases for the datasets

#     uses duckdb to query over loaded datasets - need to implement all dataset types but for example joining over vector stores
#     """
#     table_names = re.findall(
#         r"\b(?:FROM|JOIN)\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)?)", query, re.IGNORECASE
#     )
#     map_table_names = {n: n.replace(".", "_") for n in table_names}
#     for k, v in map_table_names.items():
#         query = query.replace(k, v)

#     L = locals()
#     for t in map_table_names.values():
#         parts = t.split("_")

#         # load the named datasets into locals so we can query the datasets with duckdb
#         L[t] = (
#             LanceDataTable.load_dataset(name=parts[0], namespace="default")
#             if len(parts) == 1
#             else LanceDataTable.load_dataset(namespace=parts[0], name=parts[1])
#         )

#     data = duckdb.query(query)

#     return data.pl()
