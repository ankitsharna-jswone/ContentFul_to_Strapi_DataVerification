import csv
import difflib
import re
from collections import defaultdict

# Configuration
CONTENTFUL_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/data/updateextracted_contentful_data.csv"
STRAPI_CSV = "Prod/csv/new_Strapi_prodv2.csv"
OUTPUT_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/Validation_Prod_V2.csv"
SIMILARITY_THRESHOLD = 0.99  # For content
METADATA_SIMILARITY_THRESHOLD = 0.99  # For title, metaTitle, metaDescription
EXACT_MATCH_FIELDS = {'categoryName', 'timeDuration', 'isThisAFeaturedArticle', 'isThisAPrimaryArticle'}
METADATA_FIELDS = ['title', 'metaTitle', 'metaDescription','linkUrl','linkText']

def normalize_content(text):
    """Normalize content fields aggressively."""
    text = re.sub(r'\W+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text

def normalize_metadata(text):
    """Normalize metadata fields preserving punctuation."""
    return re.sub(r'\s+', ' ', text).strip().lower()

def content_hash(text):
    """Create a content hash using normalized content."""
    return hash(normalize_content(text))

def advanced_diff(text1, text2):
    """Generate HTML diff for content."""
    differ = difflib.HtmlDiff(wrapcolumn=60)
    return differ.make_table(
        text1.splitlines(), 
        text2.splitlines(),
        context=True,
        numlines=3,
        fromdesc='Contentful',
        todesc='Strapi'
    )

def load_data(file_path, fields):
    """Load data preserving original values and storing normalized content hash."""
    data = defaultdict(dict)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                link = row['linkUrl'].strip()
                for field in fields:
                    data[link][field] = row.get(field, '')  # Store original value
                # Handle content
                content = row.get('content', '') if 'content' in fields else row.get('strapi_content', '')
                data[link]['content'] = content
                data[link]['content_hash'] = content_hash(content)
            except KeyError as e:
                print(f"Missing field {e} in row: {row}")
    return data

# Load data with original values
contentful_data = load_data(CONTENTFUL_CSV, METADATA_FIELDS + list(EXACT_MATCH_FIELDS) + ['content'])
strapi_data = load_data(STRAPI_CSV, METADATA_FIELDS + list(EXACT_MATCH_FIELDS) + ['strapi_content'])

# Prepare CSV headers
headers = ['linkUrl', 'status', 'content_match', 'content_similarity', 'content_diff']
for field in METADATA_FIELDS:
    headers.extend([f'{field}_contentful', f'{field}_strapi', f'{field}_similarity', f'{field}_match'])
for field in EXACT_MATCH_FIELDS:
    headers.extend([f'{field}_contentful', f'{field}_strapi', f'{field}_match'])
headers.extend(['missing_in_strapi', 'missing_in_contentful'])

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(headers)

    for url in set(contentful_data.keys()).union(strapi_data.keys()):
        row = {
            'linkUrl': url,
            'status': '✅ Valid',
            'content_match': '✅',
            'content_similarity': 1.0,
            'content_diff': '',
            'missing_in_strapi': '❌' if url not in strapi_data else '',
            'missing_in_contentful': '❌' if url not in contentful_data else '',
        }

        # Initialize field data
        for field in METADATA_FIELDS + list(EXACT_MATCH_FIELDS):
            row[f'{field}_contentful'] = contentful_data.get(url, {}).get(field, '')
            row[f'{field}_strapi'] = strapi_data.get(url, {}).get(field, '')
            row[f'{field}_similarity'] = ''  # Only metadata fields use this
            row[f'{field}_match'] = '✅'

        # Check presence
        if row['missing_in_strapi'] or row['missing_in_contentful']:
            row['status'] = '❌ Missing'
            writer.writerow([row[h] for h in headers])
            continue

        # Compare Content
        c_content = normalize_content(contentful_data[url]['content'])
        s_content = normalize_content(strapi_data[url]['strapi_content'])
        if contentful_data[url]['content_hash'] != strapi_data[url].get('content_hash', ''):
            similarity = difflib.SequenceMatcher(None, c_content, s_content).ratio()
            row['content_similarity'] = round(similarity, 2)
            if similarity < SIMILARITY_THRESHOLD:
                row['content_match'] = '❌'
                row['content_diff'] = advanced_diff(contentful_data[url]['content'], strapi_data[url]['strapi_content'])

        # Compare Metadata Fields
        metadata_mismatch = False
        for field in METADATA_FIELDS:
            c_val = normalize_metadata(row[f'{field}_contentful'])
            s_val = normalize_metadata(row[f'{field}_strapi'])
            similarity = difflib.SequenceMatcher(None, c_val, s_val).ratio()
            row[f'{field}_similarity'] = round(similarity, 2)
            if similarity < METADATA_SIMILARITY_THRESHOLD:
                metadata_mismatch = True
                row[f'{field}_match'] = '❌'

        # Compare Exact Match Fields
        exact_mismatch = False
        for field in EXACT_MATCH_FIELDS:
            c_val = normalize_metadata(row[f'{field}_contentful'])
            s_val = normalize_metadata(row[f'{field}_strapi'])
            if c_val != s_val:
                exact_mismatch = True
                row[f'{field}_match'] = '❌'

        # Update overall status
        if row['content_match'] == '❌' or metadata_mismatch or exact_mismatch:
            row['status'] = '❌ Mismatch'

        writer.writerow([row[h] for h in headers])

print(f"Validation complete! Results saved to {OUTPUT_CSV}")