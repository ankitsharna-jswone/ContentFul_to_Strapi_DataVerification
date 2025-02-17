import json
import csv
import os
import ijson  # For handling large JSON files
from bs4 import BeautifulSoup  # To clean HTML tags

# Function to clean and extract text from deeply nested content
def extract_text_from_block(block):
    """Recursively extracts and cleans text from nested content structures."""
    content_text = []
    
    if isinstance(block, dict):
        # Check for text in known keys
        if "value" in block and isinstance(block["value"], str):
            content_text.append(block["value"].strip())

        # Process nested content
        if "content" in block and isinstance(block["content"], list):
            for sub_block in block["content"]:
                content_text.extend(extract_text_from_block(sub_block))

    elif isinstance(block, list):  # Handle list-based content
        for item in block:
            content_text.extend(extract_text_from_block(item))

    return content_text

# Function to process `detailInfo` and extract structured content
def extract_text_from_content(content_blocks):
    """Handles various content structures and extracts readable text."""
    full_text = []
    
    if not isinstance(content_blocks, list):
        return ""

    for block in content_blocks:
        full_text.extend(extract_text_from_block(block))

    return "\n\n".join(filter(None, full_text))  # Keep structure

# Function to safely extract fields from a dictionary
def safe_extract(data, key, default="N/A"):
    """Safely retrieves values from nested JSON structures."""
    value = data.get(key, default)
    if isinstance(value, dict):  # Handle language-based JSON fields (like en-US)
        return value.get("en-US", default)
    return str(value) if value not in (None, "") else default

# Main processing function
def process_json(json_file_path, csv_file):
    """Processes the JSON file and extracts relevant information into a CSV."""
    if not os.path.exists(json_file_path):
        print(f"❌ Error: File '{json_file_path}' not found.")
        return

    # Define CSV headers (including new fields)
    fields = [
        "contentfulId", "title", "metaTitle", "metaDescription", "categoryName",
        "timeDuration", "linkUrl", "linkText", "isThisAFeaturedArticle", "isThisAPrimaryArticle", "content"
    ]

    # Open CSV file for writing
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fields)  # Write header

        # Read JSON using streaming mode
        with open(json_file_path, "r", encoding="utf-8") as file:
            blogs = ijson.items(file, "items.item")

            for count, blog in enumerate(blogs, 1):
                try:
                    sys_data = blog.get("sys", {})
                    fields_data = blog.get("fields", {})

                    # Extract basic metadata
                    contentful_id = sys_data.get("id", "N/A")  # Mapped to contentfulId

                    title = safe_extract(fields_data, "title")
                    meta_title = safe_extract(fields_data, "metaTitle")
                    meta_desc = safe_extract(fields_data, "metaDescription")
                    category = safe_extract(fields_data, "categoryName")
                    time_duration = safe_extract(fields_data, "timeDuration")
                    link_url = safe_extract(fields_data, "linkUrl")
                    link_text = safe_extract(fields_data, "linkText")
                    is_featured = safe_extract(fields_data, "isThisAFeaturedArticle")  # ✅ Found in JSON
                    is_primary = safe_extract(fields_data, "isThisAPrimaryArticle")  # ✅ Found in JSON
        
                    # Extract content from `detailInfo`
                    detail_info = fields_data.get("detailInfo", {}).get("en-US", {})
                    content_blocks = detail_info.get("content", []) if isinstance(detail_info, dict) else []
                    final_content = extract_text_from_content(content_blocks)

                    # Write extracted data to CSV
                    writer.writerow([
                        contentful_id, title, meta_title, meta_desc, category, time_duration,
                        link_url, link_text, is_featured, is_primary,
                        final_content
                    ])

                    # Show progress
                    if count % 50 == 0:
                        print(f"✅ Processed {count} blogs...")

                except Exception as e:
                    print(f"⚠️ Error processing blog {count}: {e}")
                    continue

    print(f"🎉 Successfully processed {count} blogs. Output saved to {csv_file}")

# Run the script
if __name__ == "__main__":
    json_path = "Prod/data/newcontent.json"
    output_csv = "Prod/csv/updateextracted_contentful_data.csv"
    process_json(json_path, output_csv)

print(f"✅ Extraction complete! Check the output: {output_csv}")
