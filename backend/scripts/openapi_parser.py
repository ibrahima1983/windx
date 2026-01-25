import json

import pandas as pd


def parse_openapi_schema(file_path):
    """
    Parse OpenAPI schema JSON file and extract key information into pandas DataFrames.

    Args:
        file_path: Path to the OpenAPI JSON file

    Returns:
        dict: Dictionary containing multiple DataFrames with parsed data
    """

    # Read JSON file
    with open(file_path) as f:
        schema = json.load(f)

    # Extract API information
    api_info = {
        "Title": [schema.get("info", {}).get("title", "N/A")],
        "Version": [schema.get("info", {}).get("version", "N/A")],
        "Description": [schema.get("info", {}).get("description", "N/A")],
        "OpenAPI Version": [schema.get("openapi", "N/A")],
    }
    api_info_df = pd.DataFrame(api_info)

    # Extract endpoints information
    endpoints = []
    paths = schema.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict):
                endpoint = {
                    "Path": path,
                    "Method": method.upper(),
                    "Operation ID": details.get("operationId", "N/A"),
                    "Summary": details.get("summary", "N/A"),
                    "Description": details.get("description", "N/A")[:100] + "..."
                    if details.get("description", "")
                    else "N/A",
                    "Tags": ", ".join(details.get("tags", [])),
                    "Security Required": "Yes" if details.get("security") else "No",
                }
                endpoints.append(endpoint)

    endpoints_df = pd.DataFrame(endpoints)

    # Extract response codes for each endpoint
    responses = []
    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict) and "responses" in details:
                for status_code, response_detail in details["responses"].items():
                    responses.append(
                        {
                            "Path": path,
                            "Method": method.upper(),
                            "Status Code": status_code,
                            "Description": response_detail.get("description", "N/A"),
                        }
                    )

    responses_df = pd.DataFrame(responses)

    # Extract schemas/components
    schemas = []
    components = schema.get("components", {}).get("schemas", {})

    for schema_name, schema_detail in components.items():
        schemas.append(
            {
                "Schema Name": schema_name,
                "Type": schema_detail.get("type", "N/A"),
                "Properties Count": len(schema_detail.get("properties", {})),
                "Required Fields": ", ".join(schema_detail.get("required", [])),
            }
        )

    schemas_df = pd.DataFrame(schemas)

    return {
        "api_info": api_info_df,
        "endpoints": endpoints_df,
        "responses": responses_df,
        "schemas": schemas_df,
    }


def display_summary(dataframes):
    """Display summary statistics and data."""

    print("=" * 80)
    print("API INFORMATION")
    print("=" * 80)
    print(dataframes["api_info"].to_string(index=False))
    print()

    print("=" * 80)
    print(f"ENDPOINTS SUMMARY (Total: {len(dataframes['endpoints'])})")
    print("=" * 80)
    print(dataframes["endpoints"].to_string(index=False))
    print()

    print("=" * 80)
    print("ENDPOINTS BY METHOD")
    print("=" * 80)
    method_counts = dataframes["endpoints"]["Method"].value_counts()
    print(method_counts.to_string())
    print()

    print("=" * 80)
    print("ENDPOINTS BY TAG")
    print("=" * 80)
    # Count endpoints by tag (handling multiple tags)
    tags_list = []
    for tags in dataframes["endpoints"]["Tags"]:
        if tags:
            tags_list.extend([t.strip() for t in tags.split(",")])
    if tags_list:
        tags_series = pd.Series(tags_list)
        print(tags_series.value_counts().to_string())
    print()

    print("=" * 80)
    print(f"RESPONSE CODES SUMMARY (Total: {len(dataframes['responses'])})")
    print("=" * 80)
    response_counts = dataframes["responses"]["Status Code"].value_counts()
    print(response_counts.to_string())
    print()

    if not dataframes["schemas"].empty:
        print("=" * 80)
        print(f"SCHEMAS/COMPONENTS (Total: {len(dataframes['schemas'])})")
        print("=" * 80)
        print(dataframes["schemas"].to_string(index=False))
        print()


def export_to_excel(dataframes, output_file="openapi_analysis.xlsx"):
    """Export all DataFrames to an Excel file with multiple sheets."""

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        dataframes["api_info"].to_excel(writer, sheet_name="API Info", index=False)
        dataframes["endpoints"].to_excel(writer, sheet_name="Endpoints", index=False)
        dataframes["responses"].to_excel(writer, sheet_name="Responses", index=False)
        if not dataframes["schemas"].empty:
            dataframes["schemas"].to_excel(writer, sheet_name="Schemas", index=False)

    print(f"✓ Data exported to {output_file}")


# Example usage
if __name__ == "__main__":
    # Specify your OpenAPI JSON file path
    json_file = "openapi_schema.json"

    try:
        # Parse the schema
        print(f"Reading OpenAPI schema from: {json_file}\n")
        dataframes = parse_openapi_schema(json_file)

        # Display summary
        display_summary(dataframes)

        # Export to Excel (optional)
        # export_to_excel(dataframes)

        # Save individual CSVs (optional)
        dataframes["endpoints"].to_csv("endpoints.csv", index=False)
        print("✓ Endpoints exported to endpoints.csv")

    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
        print("Please make sure the OpenAPI JSON file exists in the current directory.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{json_file}'")
    except Exception as e:
        print(f"Error: {e}")
