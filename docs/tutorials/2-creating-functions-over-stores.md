---
description: How we discover stores and functions to query them
---

# 2 Creating functions over stores

The agent has an `available_functions_search` that it can use to lookup functions. It can also be supplied with a list of functions up front. We always want to use the supplied functions and only fall back to the search if needed. This means the functions also need to be describe what they can do (and cannot do) so the interpret will use them first if it is sensible to do so.

