import json
import csv
import os
from collections.abc import Iterable
import ijson

# Enhanced text extraction with improved node handling
def extract_text_from_block(block):
    """Extract text from nested content blocks, including special node types."""
    content = []
    
    if isinstance(block, dict):
        # Direct text extraction from known keys
        for text_key in ['value', 'text', 'title', 'description']:
            if text_key in block and isinstance(block[text_key], str):
                text = block[text_key].strip()
                if text:
                    content.append(text)
        
        # Special handling for hyperlinks
        if block.get('nodeType') == 'hyperlink':
            link_text = ' '.join(extract_text_from_block(block.get('content', [])))
            if link_text:
                content.append(link_text)
        
        # Recursive content processing
        for content_key in ['content', 'children']:
            if content_key in block:
                content.extend(extract_text_from_block(block[content_key]))
                
    elif isinstance(block, Iterable) and not isinstance(block, str):
        for item in block:
            content.extend(extract_text_from_block(item))
            
    return content

# Enhanced content structure parser
def extract_text_from_content(content_blocks):
    """Process content blocks with improved structure preservation."""
    full_content = []
    
    for block in content_blocks:
        try:
            node_type = block.get('nodeType', '').lower()
            block_text = extract_text_from_block(block)
            
            # Structural formatting
            if node_type.startswith('heading'):
                full_content.append(f'\n{" ".join(block_text).upper()}\n')
            elif node_type in ['unordered-list', 'ordered-list']:
                list_items = [f'• {item}' if node_type == 'unordered-list' else f'{idx+1}. {item}' 
                            for idx, item in enumerate(block_text)]
                full_content.append('\n'.join(list_items))
            elif node_type == 'table':
                table_rows = []
                for row in block.get('content', []):
                    cells = [cell_text.strip() for cell_text in extract_text_from_block(row)]
                    table_rows.append(' | '.join(cells))
                full_content.append('TABLE:\n' + '\n'.join(table_rows))
            else:
                full_content.append(' '.join(block_text))
                
        except Exception as e:
            print(f"Error processing block: {str(e)}")
            continue
            
    return '\n\n'.join(filter(None, full_content))

# Robust field extraction with fallbacks
def safe_extract(data, keys, default=""):
    """Safely extract nested data with multiple fallback keys."""
    if isinstance(keys, str):
        keys = [keys]
        
    for key in keys:
        try:
            if key in data:
                value = data[key]
                if isinstance(value, dict):
                    return value.get('en-US', default)
                return str(value) if value not in (None, "") else default
        except:
            continue
    return default

def main():
    json_path = os.path.abspath("NewScript/resut.json")
    csv_path = os.path.abspath("update.csv")

    fields = [
        "id", "title", "metaTitle", "metaDescription", "categoryName",
        "tagsList", "conceptsList", "linkUrl", "createdAt", 
        "updatedAt", "timeDuration", "content"
    ]

    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        writer.writerow(fields)

        with open(json_path, 'r', encoding='utf-8') as file:
            items = ijson.items(file, 'items.item')
            
            for idx, item in enumerate(items, 1):
                try:
                    sys_data = item.get('sys', {})
                    fields_data = item.get('fields', {})
                    metadata = item.get('metadata', {})

                    # Extract core fields
                    row_data = [
                        sys_data.get('id', 'N/A'),
                        safe_extract(fields_data, 'title'),
                        safe_extract(fields_data, 'metaTitle'),
                        safe_extract(fields_data, 'metaDescription'),
                        safe_extract(fields_data, 'categoryName'),
                        ', '.join([t.get('name', '') for t in metadata.get('tags', [])]),
                        ', '.join(metadata.get('concepts', [])),
                        safe_extract(fields_data, 'linkUrl'),
                        sys_data.get('createdAt', 'N/A'),
                        sys_data.get('updatedAt', 'N/A'),
                        safe_extract(fields_data, 'timeDuration')
                    ]

                    # Extract and structure content
                    detail_info = fields_data.get('detailInfo', {})
                    content_blocks = detail_info.get('content', []) if isinstance(detail_info, dict) else []
                    structured_content = extract_text_from_content(content_blocks)
                    row_data.append(structured_content)

                    writer.writerow(row_data)

                    # Progress monitoring
                    if idx % 10 == 0:
                        print(f"Processed {idx} items...")
                        
                except Exception as e:
                    print(f"Skipping item {idx} due to error: {str(e)}")
                    continue

    print(f"Successfully processed {idx} items. Output saved to {csv_path}")

if __name__ == "__main__":
    main()