import json
import csv

# Load the JSON file
json_file_path = "data/content.json"

with open(json_file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

# Open CSV file for writing
csv_file_path = "data/content_extracted_data.csv"

with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile)

    # Write header (aligned with Strapi fields)
    csv_writer.writerow([
        "ID", "Name", "Title", "Meta Title", "Meta Description",
        "Canonical", "URN", "Mapping Name", "Content Menu", "Content"
    ])

    def extract_text_from_content(content_list):
        """Extracts all text from rich content structures, handling paragraphs, lists, and other nodes."""
        extracted_text = []
        for content_item in content_list:
            if content_item.get("nodeType") == "paragraph":
                paragraph_text = []
                for text in content_item.get("content", []):
                    if text.get("nodeType") == "text":
                        paragraph_text.append(text.get("value", "").strip())
                if paragraph_text:
                    extracted_text.append(" ".join(paragraph_text))  # Join paragraph text properly

            elif content_item.get("nodeType") == "unordered-list":
                for list_item in content_item.get("content", []):
                    if list_item.get("nodeType") == "list-item":
                        for list_text in list_item.get("content", []):
                            if list_text.get("nodeType") == "paragraph":
                                for text in list_text.get("content", []):
                                    if text.get("nodeType") == "text":
                                        extracted_text.append(f"- {text.get('value', '').strip()}")  # Add bullet point

        return "\n".join(extracted_text) if extracted_text else "N/A"

    # Extract relevant data
    for item in data.get("items", []):
        sys_data = item.get("sys", {})
        fields = item.get("fields", {})

        item_id = sys_data.get("id", "N/A")
        name = fields.get("name", {}).get("en-US", "N/A")
        title = fields.get("title", {}).get("en-US", "N/A")
        meta_title = fields.get("metaTitle", {}).get("en-US", "N/A")
        meta_description = fields.get("metaDescription", {}).get("en-US", "N/A")
        canonical = fields.get("canonical", {}).get("en-US", "N/A")
        urn = sys_data.get("urn", "N/A")
        mapping_name = sys_data.get("contentType", {}).get("sys", {}).get("id", "N/A")

        # ✅ Extract `contentMenu` properly
        raw_content_menu = fields.get("contentMenu", {}).get("en-US", {})
        content_menu_text = extract_text_from_content(raw_content_menu.get("content", [])) if isinstance(raw_content_menu, dict) else "N/A"

        # ✅ Extract `content` properly, including paragraphs and lists
        content_data = fields.get("content", {}).get("en-US", {})
        content_text = extract_text_from_content(content_data.get("content", []))

        # Write row
        csv_writer.writerow([
            item_id, name, title, meta_title, meta_description,
            canonical, urn, mapping_name, content_menu_text, content_text
        ])

print(f"✅ Data extracted and saved to: {csv_file_path}")
