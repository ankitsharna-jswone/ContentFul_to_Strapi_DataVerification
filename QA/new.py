import json
import csv

# Load JSON data
json_file_path = "NewScript/read.json"

with open(json_file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

# Extract blog entries
blogs = data.get("items", [])

# Define CSV output file
csv_file = "prod_blogs_data.csv"

# Define CSV columns
fields = [
    "id", "title", "metaTitle", "metaDescription", "categoryName", "tagsList",
    "conceptsList", "linkUrl", "createdAt", "updatedAt", "timeDuration", "content"
]

# Function to extract all text from deeply nested content blocks
def extract_text_from_block(block, depth=0):
    content_text = []
    
    # If the block contains direct text, extract it
    if "value" in block:
        text_value = block["value"].strip()

        # Remove "Contentful - " prefix if present
        if text_value.startswith("Contentful - "):
            text_value = text_value.replace("Contentful - ", "", 1)

        content_text.append(text_value)

    # If the block contains more nested content, traverse deeper
    if "content" in block:
        for sub_block in block["content"]:
            content_text.extend(extract_text_from_block(sub_block, depth + 1))

    return content_text

# Function to extract all text content from `detailInfo`
def extract_text_from_content(content_blocks):
    content_text = []

    for block in content_blocks:
        # Extract paragraph and heading text
        if block.get("nodeType") in ["paragraph", "heading-1", "heading-2", "heading-3",
                                     "heading-4", "heading-5", "heading-6"]:
            content_text.extend(extract_text_from_block(block))

        # Extract unordered list items
        elif block.get("nodeType") == "unordered-list":
            for list_item in block.get("content", []):
                for sub_block in list_item.get("content", []):
                    if sub_block.get("nodeType") == "paragraph":
                        for text_block in sub_block.get("content", []):
                            if isinstance(text_block, dict) and "value" in text_block:
                                content_text.append(f"• {text_block['value'].strip()}")

        # Extract ordered list items
        elif block.get("nodeType") == "ordered-list":
            index = 1
            for list_item in block.get("content", []):
                for sub_block in list_item.get("content", []):
                    if sub_block.get("nodeType") == "paragraph":
                        for text_block in sub_block.get("content", []):
                            if isinstance(text_block, dict) and "value" in text_block:
                                content_text.append(f"{index}. {text_block['value'].strip()}")
                                index += 1

        # Extract table content
        elif block.get("nodeType") == "table":
            for row in block.get("content", []):
                row_text = []
                for cell in row.get("content", []):
                    for text_block in cell.get("content", []):
                        if isinstance(text_block, dict) and "value" in text_block:
                            row_text.append(text_block["value"].strip())
                if row_text:
                    content_text.append(" | ".join(row_text))

    return "\n".join(content_text)  # Keep all extracted lines separate

# Write CSV file
with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(fields)  # Write header

    for blog in blogs:
        blog_id = blog["sys"]["id"]
        title = blog["fields"].get("title", "N/A")
        meta_title = blog["fields"].get("metaTitle", "N/A")
        meta_desc = blog["fields"].get("metaDescription", "N/A")
        category = blog["fields"].get("categoryName", "N/A")
        tags = ", ".join(blog["fields"].get("tagsList", []))
        concepts = ", ".join(blog["metadata"].get("concepts", []))
        link = blog["fields"].get("linkUrl", "N/A")
        created_at = blog["sys"].get("createdAt", "N/A")
        updated_at = blog["sys"].get("updatedAt", "N/A")
        time_duration = blog["fields"].get("timeDuration", "N/A")

        # Extract detailed content
        content_blocks = blog["fields"].get("detailInfo", {}).get("content", [])
        final_content = extract_text_from_content(content_blocks)

        # Write data row
        writer.writerow([blog_id, title, meta_title, meta_desc, category, tags, concepts, link, created_at, updated_at, time_duration, final_content])

print(f"✅ Data extracted and saved to {csv_file}")
