import json
import csv
import re
from html import unescape

# Load the JSON file
json_file_path = "data/strapi.json"

with open(json_file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

# Open CSV file for writing
csv_file_path = "data/strapi_extracted_data.csv"

with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
    csv_writer = csv.writer(csvfile)

    # Write header (dates removed)
    csv_writer.writerow([
        "ID", "Name", "Title", "Meta Title", "Meta Description",
        "Canonical", "Contentful ID", "Mapping Name", "Content Menu", "Content"
    ])

    def clean_html(text):
        """Removes HTML tags and decodes HTML entities (like &nbsp;, &amp;)"""
        if not isinstance(text, str):
            return "N/A"
        text = unescape(text)  # Convert HTML entities (e.g., &nbsp; -> space, &amp; -> &)
        text = re.sub(r"<.*?>", "", text)  # Remove HTML tags
        text = re.sub(r"\s+", " ", text).strip()  # Normalize spaces
        return text if text else "N/A"

    def extract_content_menu(content_menu):
        """Extracts text from contentMenu field and ensures proper spacing."""
        menu_items = []

        if isinstance(content_menu, dict) and "content" in content_menu:
            for item in content_menu["content"]:
                if item.get("nodeType") == "paragraph":
                    for text in item.get("content", []):
                        if text.get("nodeType") == "text":
                            menu_items.append(text.get("value", "").strip())

        elif isinstance(content_menu, list):
            for item in content_menu:
                menu_items.append(clean_html(str(item)))

        elif isinstance(content_menu, str):
            return clean_html(content_menu)

        menu_text = " | ".join(menu_items) if menu_items else "N/A"

        # ✅ Ensure proper spacing between numbered items
        menu_text = re.sub(r"(\d+)\.([A-Za-z])", r"\1. \2", menu_text)  # Add space after "1.Information" -> "1. Information"
        return menu_text

    def extract_content(content):
        """Extracts content text without changing its formatting."""
        return clean_html(content)  # Keeps content extraction as it was!

    # Extract relevant data
    for item in data.get("data", []):
        item_id = item.get("id", "N/A")
        attributes = item.get("attributes", {})

        name = clean_html(attributes.get("name", "N/A"))
        title = clean_html(attributes.get("title", "N/A"))
        meta_title = clean_html(attributes.get("metaTitle", "N/A"))
        meta_description = clean_html(attributes.get("metaDescription", "N/A"))
        canonical = clean_html(attributes.get("canonical", "N/A"))
        contentful_id = clean_html(attributes.get("contentfulId", "N/A"))
        mapping_name = clean_html(attributes.get("mappingName", "N/A"))

        # Extract contentMenu properly and ensure spacing
        content_menu = extract_content_menu(attributes.get("contentMenu", "N/A"))

        # Extract main content (unchanged)
        content = extract_content(attributes.get("content", "N/A"))

        # Write to CSV
        csv_writer.writerow([
            item_id, name, title, meta_title, meta_description,
            canonical, contentful_id, mapping_name, content_menu, content
        ])

print(f"✅ Data extracted and saved to: {csv_file_path}")
