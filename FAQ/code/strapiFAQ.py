import json
import csv
from collections import defaultdict

# Load JSON data
file_path = "strapiFAQ.json"
with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

# Extract required fields
def extract_field(item, field_name):
    return item.get("attributes", {}).get(field_name, "")

# Dictionary to store combined data for duplicate IDs
data_dict = defaultdict(lambda: {"title": "", "description": "", "slug": "", "metaTitle": "", "metaDescription": ""})

for item in data.get("data", []):
    entry_id = item["id"]
    title = extract_field(item, "title")
    description = extract_field(item, "description")
    slug = extract_field(item, "slug")
    meta_title = extract_field(item, "metaTitle")
    meta_description = extract_field(item, "metaDescription")
    
    # Combine duplicate entries
    data_dict[entry_id]["title"] = data_dict[entry_id]["title"] or title
    data_dict[entry_id]["description"] += (" " + description if description else "")
    data_dict[entry_id]["slug"] = data_dict[entry_id]["slug"] or slug
    data_dict[entry_id]["metaTitle"] = data_dict[entry_id]["metaTitle"] or meta_title
    data_dict[entry_id]["metaDescription"] += (" " + meta_description if meta_description else "")

# Write to CSV
output_file = "extracted_strapi_faqs.csv"
with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["Id", "Title", "Description", "Slug", "Meta Title", "Meta Description"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    
    for entry_id, values in data_dict.items():
        writer.writerow({
            "Id": entry_id,
            "Title": values["title"].strip(),
            "Description": values["description"].strip(),
            "Slug": values["slug"].strip(),
            "Meta Title": values["metaTitle"].strip(),
            "Meta Description": values["metaDescription"].strip()
        })

print(f"Data successfully extracted and saved to {output_file}")
