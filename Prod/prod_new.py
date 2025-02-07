import json
import csv
import os
from collections.abc import Iterable
import ijson  # For iterative JSON parsing

# Function to extract text from a content block (handles deep nesting)
def extract_text_from_block(block):
    """Extract text from a content block, handling deep nesting and multiple text locations."""
    content_text = []
    
    try:
        # Handle text nodes
        if isinstance(block, dict):
            # Check multiple possible text locations
            for key in ['value', 'text', 'content']:
                if key in block and isinstance(block[key], str):
                    text = block[key].strip()
                    if text:
                        if key == 'value' and text.startswith("Contentful - "):
                            text = text.replace("Contentful - ", "", 1)
                        content_text.append(text)
                        break  # Prioritize first valid text found
            
            # Recursive content handling
            if 'content' in block:
                for sub_block in block.get('content', []):
                    content_text.extend(extract_text_from_block(sub_block))
                    
        # Handle list-based content structures
        elif isinstance(block, Iterable) and not isinstance(block, str):
            for item in block:
                content_text.extend(extract_text_from_block(item))
                
    except Exception as e:
        print(f"Block extraction error: {str(e)}")
        if os.getenv('DEBUG'):
            print(f"Problem block: {json.dumps(block, indent=2)}")
            
    return content_text

# Function to extract structured content from `detailInfo`
def extract_text_from_content(content_blocks):
    """Extract structured content from `detailInfo`, handling various node types."""
    full_text = []
    
    if not isinstance(content_blocks, list):
        print("⚠️ Content blocks is not a list")
        return ''
    
    for idx, block in enumerate(content_blocks):
        try:
            node_type = block.get('nodeType', 'unknown').lower()
            
            # Unified content extraction
            block_text = extract_text_from_block(block)
            
            if node_type.startswith('heading'):
                full_text.append('\n' + ' '.join(block_text) + '\n')
            elif node_type in ['unordered-list', 'ordered-list']:
                list_items = []
                for item in block.get('content', []):
                    item_text = extract_text_from_block(item)
                    if item_text:
                        prefix = '• ' if node_type == 'unordered-list' else f"{len(list_items)+1}. "
                        list_items.append(prefix + ' '.join(item_text))
                full_text.append('\n'.join(list_items))
            elif node_type == 'table':
                rows = []
                for row in block.get('content', []):
                    cells = [ ' '.join(extract_text_from_block(cell)) 
                            for cell in row.get('content', []) ]
                    rows.append(' | '.join(cells))
                full_text.append('\n'.join(rows))
            else:
                full_text.append(' '.join(block_text))
                
        except Exception as e:
            print(f"⚠️ Error processing block {idx}: {str(e)}")
            if os.getenv('DEBUG'):
                print(f"Problematic block data: {json.dumps(block, indent=2)}")
    
    # Join with double newlines to preserve structure
    return '\n\n'.join(filter(None, full_text))

# Function to safely extract text (handles string or dictionary format)
def safe_extract(data, key, default="N/A"):
    """Safely extract a value from a dictionary, handling nested structures."""
    try:
        value = data.get(key, default)
        if isinstance(value, dict):  # Handles cases like { "en-US": "value" }
            return value.get("en-US", default)
        return str(value) if value not in (None, "") else default
    except Exception as e:
        print(f"⚠️ Error extracting key '{key}': {e}")
        return default

# Main function to process JSON and write to CSV
def main():
    # Use absolute paths for reliability
    json_file_path = os.path.abspath("NewScript/prod/resut.json")
    csv_file = os.path.abspath("update.csv")

    if not os.path.exists(json_file_path):
        print(f"❌ Error: File '{json_file_path}' not found.")
        return

    # Define CSV headers
    fields = [
        "id", "title", "metaTitle", "metaDescription", "categoryName", 
        "tagsList", "conceptsList", "linkUrl", "createdAt", 
        "updatedAt", "timeDuration", "content"
    ]

    # Open CSV file for writing
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fields)  # Write header

        # Stream JSON items one by one
        with open(json_file_path, "r", encoding="utf-8") as file:
            blogs = ijson.items(file, "items.item")
            
            for count, blog in enumerate(blogs, 1):
                try:
                    # Extract metadata fields
                    sys_data = blog.get("sys", {})
                    fields_data = blog.get("fields", {})
                    metadata = blog.get("metadata", {})

                    # ID and Dates
                    blog_id = sys_data.get("id", "N/A")
                    created_at = sys_data.get("createdAt", "N/A")
                    updated_at = sys_data.get("updatedAt", "N/A")

                    # Fields
                    title = safe_extract(fields_data, "title")
                    meta_title = safe_extract(fields_data, "metaTitle")
                    meta_desc = safe_extract(fields_data, "metaDescription")
                    category = safe_extract(fields_data, "categoryName")
                    link = safe_extract(fields_data, "linkUrl")
                    time_duration = safe_extract(fields_data, "timeDuration")

                    # Metadata
                    tags = ", ".join([tag.get("name", "") for tag in metadata.get("tags", [])])
                    concepts = ", ".join(metadata.get("concepts", []))

                    # Extract `detailInfo` content safely
                    detail_info = fields_data.get("detailInfo", {})
                    content_blocks = detail_info.get("content", []) if isinstance(detail_info, dict) else []
                    final_content = extract_text_from_content(content_blocks)

                    # Write data row
                    writer.writerow([
                        blog_id, title, meta_title, meta_desc, category,
                        tags, concepts, link, created_at, updated_at,
                        time_duration, final_content
                    ])

                    # Progress Indicator
                    if count % 100 == 0:
                        print(f"Processed {count} items...")
                
                except Exception as e:
                    print(f"⚠️ Error processing item {count}: {e}")
                    continue

    print(f"✅ Successfully processed {count} items. Output saved to {csv_file}")

if __name__ == "__main__":
    main()