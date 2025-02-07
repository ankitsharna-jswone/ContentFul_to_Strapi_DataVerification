import csv
import difflib
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configuration
CONTENTFUL_CSV = "QA/blogs_data.csv"
STRAPI_CSV = "QA/strapi_extracted_data.csv"
OUTPUT_CSV = "./improved_validation_results.csv"
SIMILARITY_THRESHOLD = 0.95  # Stricter threshold for content matching
EXACT_MATCH_FIELDS = {'categoryName', 'timeDuration'}  # Fields requiring exact matches

def normalize_text(text):
    """Enhanced text normalization"""
    text = re.sub(r'\W+', ' ', text)  # Remove non-word characters
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text

def content_hash(text):
    """Create a quick content hash for fast comparison"""
    return hash(normalize_text(text))

def advanced_diff(text1, text2):
    """Improved diff generator with context"""
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
    """Load data with error handling and field validation"""
    data = defaultdict(dict)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                link = row['linkUrl'].strip()
                for field in fields:
                    data[link][field] = normalize_text(row.get(field, ''))
                # Add content hash for quick comparison
                data[link]['content_hash'] = content_hash(row.get('content', '') if 'content' in fields else row.get('strapi_content', ''))
            except KeyError as e:
                print(f"Missing expected field {e} in row: {row}")
    return data

# Field mappings between systems
CONTENTFUL_FIELDS = ['title', 'metaTitle', 'metaDescription', 'categoryName', 
                    'timeDuration', 'content']
STRAPI_FIELDS = ['title', 'metaTitle', 'metaDescription', 'categoryName',
                'timeDuration', 'strapi_content']

# Load datasets
contentful_data = load_data(CONTENTFUL_CSV, CONTENTFUL_FIELDS)
strapi_data = load_data(STRAPI_CSV, STRAPI_FIELDS)

# Find all unique URLs from both systems
all_urls = set(contentful_data.keys()).union(set(strapi_data.keys()))

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    headers = [
        'linkUrl', 'status', 'content_match', 'metadata_match',
        'missing_in_strapi', 'missing_in_contentful', 'content_similarity',
        'exact_field_mismatches', 'content_diff'
    ]
    writer.writerow(headers)

    for url in all_urls:
        row_data = {
            'linkUrl': url,
            'status': '✅ Valid',
            'content_match': '✅',
            'metadata_match': '✅',
            'missing_in_strapi': '❌' if url not in strapi_data else '',
            'missing_in_contentful': '❌' if url not in contentful_data else '',
            'content_similarity': 1.0,
            'exact_field_mismatches': [],
            'content_diff': ''
        }

        # Check for existence in both systems
        if not strapi_data.get(url) or not contentful_data.get(url):
            row_data['status'] = '❌ Missing'
            writer.writerow(row_data.values())
            continue

        # Compare exact match fields first
        mismatches = []
        for field in EXACT_MATCH_FIELDS:
            c_field = contentful_data[url].get(field, '')
            s_field = strapi_data[url].get(field, '')
            if c_field != s_field:
                mismatches.append(f"{field} (Contentful: {c_field}, Strapi: {s_field})")

        # Compare content using hash first for quick validation
        content_match = contentful_data[url]['content_hash'] == strapi_data[url]['content_hash']
        
        # If hash mismatch, calculate detailed similarity
        if not content_match:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([
                contentful_data[url].get('content', ''),
                strapi_data[url].get('strapi_content', '')
            ])
            similarity = cosine_similarity(tfidf[0], tfidf[1])[0][0]
            row_data['content_similarity'] = round(similarity, 2)
            row_data['content_match'] = '✅' if similarity >= SIMILARITY_THRESHOLD else '❌'
            
            # Generate detailed diff if similarity below threshold
            if similarity < SIMILARITY_THRESHOLD:
                row_data['content_diff'] = advanced_diff(
                    contentful_data[url].get('content', ''),
                    strapi_data[url].get('strapi_content', '')
                )

        # Check metadata fields
        metadata_fields = ['title', 'metaTitle', 'metaDescription']
        metadata_mismatch = any(
            contentful_data[url].get(field, '') != strapi_data[url].get(field, '')
            for field in metadata_fields
        )
        
        # Update final status
        if mismatches or metadata_mismatch or not content_match:
            row_data['status'] = '❌ Mismatch'
            row_data['metadata_match'] = '❌' if metadata_mismatch else '✅'
            row_data['exact_field_mismatches'] = '; '.join(mismatches)

        writer.writerow(row_data.values())

print(f"Validation complete! Results saved to {OUTPUT_CSV}")