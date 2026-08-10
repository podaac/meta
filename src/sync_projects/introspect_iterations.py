"""
Introspect the fields of CreateProjectV2FieldInput and UpdateProjectV2FieldInput.
Usage: GH_TOKEN=<token> python3 src/sync_projects/introspect_iterations.py
"""
import os
import requests

GITHUB_API = "https://api.github.com/graphql"
token = os.environ["GH_TOKEN"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

query = """
{
  __schema {
    types {
      name
      kind
      inputFields {
        name
        type { name kind ofType { name kind ofType { name kind } } }
      }
    }
  }
}
"""

r = requests.post(GITHUB_API, headers=headers, json={"query": query})
r.raise_for_status()
types = r.json()["data"]["__schema"]["types"]

targets = {
    "ProjectV2IterationFieldConfigurationInput",
}

def unwrap(type_info):
    """Recursively unwrap NON_NULL/LIST to find the named type."""
    if type_info is None:
        return "?"
    if type_info.get("name"):
        return type_info["name"]
    kind = type_info.get("kind", "")
    inner = unwrap(type_info.get("ofType"))
    if kind == "LIST":
        return f"[{inner}]"
    return inner

for t in types:
    if (t["name"] in targets or "iteration" in t["name"].lower()) and t.get("inputFields"):
        print(f"\n=== {t['name']} ===")
        for f in t["inputFields"]:
            print(f"  {f['name']}: {unwrap(f['type'])}")
