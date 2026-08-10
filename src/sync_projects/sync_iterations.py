import os
import requests

GITHUB_API = "https://api.github.com/graphql"

token = os.environ.get("GH_TOKEN")
if not token:
    raise RuntimeError("GH_TOKEN is not set")

print(f"Token length: {len(token)}")

HEADERS = {
    "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
    "Content-Type": "application/json",
}

ORG = os.environ["ORG"]
SOURCE_PROJECT_NUMBER = int(os.environ["SOURCE_PROJECT_NUMBER"])
TARGET_PROJECT_NUMBER = int(os.environ["TARGET_PROJECT_NUMBER"])


def graphql(query, variables=None):
    r = requests.post(
        GITHUB_API,
        headers=HEADERS,
        json={"query": query, "variables": variables or {}},
    )
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]


def get_project(project_number):
    query = """
    query ($org: String!, $number: Int!) {
      organization(login: $org) {
        projectV2(number: $number) {
          id
          fields(first: 50) {
            nodes {
              ... on ProjectV2IterationField {
                id
                name
                configuration {
                  startDate
                  duration
                  iterations {
                    id
                    title
                    startDate
                    duration
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    data = graphql(query, {"org": ORG, "number": project_number})
    project = data["organization"]["projectV2"]

    iteration_field = next(
        f for f in project["fields"]["nodes"]
        if f and f.get("configuration")
    )

    return project["id"], iteration_field


def sync_iterations():
    _, source_field = get_project(SOURCE_PROJECT_NUMBER)

    target_project_id, target_field = get_project(TARGET_PROJECT_NUMBER)

    source_iterations = source_field["configuration"]["iterations"]
    target_iterations = target_field["configuration"]["iterations"]

    existing_titles = {it["title"] for it in target_iterations}

    new_iterations = [it for it in source_iterations if it["title"] not in existing_titles]

    if not new_iterations:
        print("No new iterations to create.")
        return

    mutation = """
    mutation ($fieldId: ID!, $startDate: Date!, $duration: Int!, $iterations: [ProjectV2Iteration!]!) {
      updateProjectV2Field(
        input: {
          fieldId: $fieldId
          iterationConfiguration: {
            startDate: $startDate
            duration: $duration
            iterations: $iterations
          }
        }
      ) {
        projectV2Field {
          ... on ProjectV2IterationField {
            id
          }
        }
      }
    }
    """

    config = target_field["configuration"]

    for it in new_iterations:
        print(f"Creating iteration: {it['title']}")

    graphql(
        mutation,
        {
            "fieldId": target_field["id"],
            "startDate": config["startDate"],
            "duration": config["duration"],
            "iterations": [
                {"title": it["title"], "startDate": it["startDate"], "duration": it["duration"]}
                for it in new_iterations
            ],
        },
    )


if __name__ == "__main__":
    sync_iterations()