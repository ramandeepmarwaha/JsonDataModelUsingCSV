import pandas as pd
import json
import os

def create_json_schema(data):
    json_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {},
        "required": []
    }
    sample_json = {}

    def add_property(field_path, field_schema, sample_value):
        keys = field_path.split('.')
        current = json_schema["properties"]

        for key in keys[:-1]:
            if key not in current:
                # Initialize an object for the current key
                current[key] = {"type": "object", "properties": {}}
            
            # Check if the current type is an array and handle accordingly
            if current[key]["type"] == "array":
                # If it's an array, navigate into the 'items' for further nesting
                current[key]["items"] = current[key].get("items", {})
                if "type" not in current[key]["items"]:
                    current[key]["items"]["type"] = "object"
                    current[key]["items"]["properties"] = {}

                current = current[key]["items"]["properties"]
            else:
                current = current[key]["properties"]

        # Ensure the final key exists in the schema
        if keys[-1] not in current:
            current[keys[-1]] = field_schema
        else:
            # If it exists, we can merge or update the existing schema
            current[keys[-1]].update(field_schema)

        # Handle sample values
        current_sample = sample_json
        for key in keys[:-1]:
            if key not in current_sample:
                # If it's an array, initialize it as a list
                if "type" in json_schema["properties"].get(key, {}) and json_schema["properties"][key]["type"] == "array":
                    current_sample[key] = [{}]  # Initialize an array of objects
                else:
                    current_sample[key] = {}
            current_sample = current_sample[key]

        # If it's an array, place the sample value inside the array
        if isinstance(current_sample, list):
            current_sample[0][keys[-1]] = sample_value  # Use the first element of the array
        else:
            current_sample[keys[-1]] = sample_value

    for index, row in data.iterrows():
        field_name = row['Field Name']
        data_type = row['Data Type'].strip().lower()
        required = row['Required'].strip().lower() == 'yes'
        enums = row.get('Enum Values', '').strip('"').split(',') if 'Enum Values' in row and pd.notna(row['Enum Values']) else None
        is_array = row['Is Array'].strip().lower() == 'yes'

        # Initialize field schema and sample value
        field_schema = {}
        sample_value = None

        # Handle data types and structures
        if data_type == 'object':
            if is_array:
                # If it's an array of objects
                field_schema = {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {}
                    }
                }
                sample_value = [{}]  # Example for an array of objects
            else:
                field_schema = {"type": "object", "properties": {}}
                sample_value = {}
        elif is_array:
            # Generic array type (string, number, etc.)
            field_schema = {
                "type": "array",
                "items": {"type": data_type}  # Array of the specified data type
            }
            sample_value = [f"example_{data_type}"]  # Example for an array of basic types
        else:
            field_schema = {"type": data_type}
            if enums:
                field_schema["enum"] = [enum.strip() for enum in enums]

            # Assign sample values based on type
            if data_type == 'string':
                sample_value = "example_string"
            elif data_type == 'integer':
                sample_value = 0  # Default integer sample
            elif data_type == 'boolean':
                sample_value = True
            if enums:
                sample_value = enums[0].strip()

        # Add constraints if applicable
        if 'Min Length' in row and pd.notna(row['Min Length']):
            field_schema["minLength"] = int(row['Min Length'])
        if 'Max Length' in row and pd.notna(row['Max Length']):
            field_schema["maxLength"] = int(row['Max Length'])
        if 'Min Items' in row and pd.notna(row['Min Items']):
            field_schema["minItems"] = int(row['Min Items'])
        if 'Max Items' in row and pd.notna(row['Max Items']):
            field_schema["maxItems"] = int(row['Max Items'])
        if 'Default Value' in row and pd.notna(row['Default Value']):
            sample_value = row['Default Value'].strip('"')

        # Debugging output to track the properties being added
        print(f"Adding property: {field_name} with schema: {field_schema}")

        # Add property to schema and sample JSON
        add_property(field_name, field_schema, sample_value)

        # Handle required fields
        if required:
            required_path = field_name.split('.')
            for i in range(len(required_path)):
                parent_path = '.'.join(required_path[:i + 1])
                if parent_path not in json_schema["required"]:
                    json_schema["required"].append(parent_path)

    return json_schema, sample_json

# Input: Path to your CSV file
excel_file1 = "data_model.csv"  # Change to your actual CSV file path
excel_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), excel_file1)

# Load the CSV data
data = pd.read_csv(excel_file)

# Generate JSON Schema and Sample JSON
json_schema, sample_json = create_json_schema(data)

# Save JSON Schema and Sample JSON to files
with open('output_schema.json', 'w') as schema_file:
    json.dump(json_schema, schema_file, indent=4)

with open('sample_output.json', 'w') as sample_file:
    json.dump(sample_json, sample_file, indent=4)

print("JSON Schema and Sample JSON created successfully.")
