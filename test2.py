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

    def add_property(field_path, field_schema, sample_value, required):
        keys = field_path.split('.')
        current = json_schema["properties"]

        # Navigate through the keys to set up the schema structure
        for key in keys[:-1]:
            if key not in current:
                if "items" in current.get(key, {}):
                    current[key] = {"type": "array", "items": {"type": "object", "properties": {}}}
                else:
                    current[key] = {"type": "object", "properties": {}}
            elif current[key]["type"] == "array":
                if "items" not in current[key]:
                    current[key]["items"] = {"type": "object", "properties": {}}
                current = current[key]["items"]["properties"]
            else:
                current = current[key]["properties"]

        # Add the field schema
        if keys[-1] not in current:
            current[keys[-1]] = field_schema
        else:
            current[keys[-1]].update(field_schema)

        # Add to the required fields of the parent object
        if required:
            parent = json_schema
            for key in keys[:-1]:
                parent = parent["properties"][key]
            if "required" not in parent:
                parent["required"] = []
            field_name_cleaned = keys[-1].strip()
            if field_name_cleaned not in parent["required"]:
                parent["required"].append(field_name_cleaned)

        # Create the sample JSON
        current_sample = sample_json
        for key in keys[:-1]:
            if key not in current_sample:
                current_sample[key] = {}
            current_sample = current_sample[key]

        # Handle assignment for the last key
        if isinstance(current_sample, list):
            if len(current_sample) == 0:
                current_sample.append({})
            current_sample[0][keys[-1]] = sample_value
        else:
            current_sample[keys[-1]] = sample_value

    for index, row in data.iterrows():
        field_name = row['Field Name']
        data_type = row['Data Type'].strip().lower()
        required = row['Required'].strip().lower() == 'yes'
        enums = row.get('Enum Values', '').strip('"').split(',') if 'Enum Values' in row and pd.notna(row['Enum Values']) else None
        is_array = row['Is Array'].strip().lower() == 'yes'
        description = str(row.get('Description', '')).strip()
        format_type = str(row.get('Format', '')).strip().lower()
        deprecated = row.get('Deprecated', '').strip().lower() == 'yes'
        pattern = str(row.get('Pattern', '')).strip() if 'Pattern' in row and pd.notna(row['Pattern']) else None

        field_schema = {}

        # Initialize the field schema based on type
        if data_type == 'object':
            if is_array:
                field_schema = {
                    "type": "array",
                    "minItems": int(row['Min Items']) if 'Min Items' in row and pd.notna(row['Min Items']) else None,
                    "maxItems": int(row['Max Items']) if 'Max Items' in row and pd.notna(row['Max Items']) else None,
                    "items": {
                        "type": "object",
                        "properties": {}
                    }
                }
                sample_value = [{}]
            else:
                field_schema = {
                    "type": "object",
                    "properties": {}
                }
                sample_value = {}
        
        elif is_array:
            field_schema = {
                "type": "array",
                "minItems": int(row['Min Items']) if 'Min Items' in row and pd.notna(row['Min Items']) else None,
                "maxItems": int(row['Max Items']) if 'Max Items' in row and pd.notna(row['Max Items']) else None,
                "items": {
                    "type": data_type
                }
            }
            sample_value = [f"example_{data_type}"]

        else:
            field_schema = {"type": data_type}

        # Add constraints
        if enums:
            field_schema["enum"] = [enum.strip() for enum in enums]
        if data_type == 'string':
            sample_value = "example_string"
            if format_type != "nan":
                field_schema["format"] = format_type
            if pattern:
                field_schema["pattern"] = pattern
        elif data_type == 'integer':
            sample_value = 0
        elif data_type == 'boolean':
            sample_value = True
        if enums:
            sample_value = enums[0].strip()

        # Add optional constraints
        if description != "nan":
            field_schema["description"] = description
        if deprecated == "yes":
            field_schema["deprecated"] = True

        # Handle length constraints for strings
        if 'Min Length' in row and pd.notna(row['Min Length']):
            field_schema["minLength"] = int(row['Min Length'])
        if 'Max Length' in row and pd.notna(row['Max Length']):
            field_schema["maxLength"] = int(row['Max Length'])

        if 'Default Value' in row and pd.notna(row['Default Value']):
            sample_value = row['Default Value'].strip('"')

        add_property(field_name, field_schema, sample_value, required)

    # Clean up empty 'required' lists from all levels
    def remove_empty_required(obj):
        if isinstance(obj, dict):
            if "required" in obj and not obj["required"]:
                del obj["required"]
            for value in obj.values():
                remove_empty_required(value)
        elif isinstance(obj, list):
            for item in obj:
                remove_empty_required(item)

    remove_empty_required(json_schema)

    return json_schema, sample_json

# Input: Path to your CSV file
excel_file1 = "data_model.csv"  # Change to your actual CSV file path
excel_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), excel_file1)

# Load the CSV data
data = pd.read_csv(excel_file)

# Generate JSON Schema and Sample JSON
json_schema, sample_json = create_json_schema(data)

# Save JSON Schema and Sample JSON to files
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output_schema.json'), 'w') as schema_file:
    json.dump(json_schema, schema_file, indent=4)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sample_output.json'), 'w') as sample_file:
    json.dump(sample_json, sample_file, indent=4)

print("JSON Schema and Sample JSON created successfully.")
