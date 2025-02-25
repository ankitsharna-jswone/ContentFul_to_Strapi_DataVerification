import csv
import difflib
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configuration
CONTENTFUL_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/updateextracted_contentful_data.csv"
STRAPI_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/new_Strapi_prod.csv"
OUTPUT_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/newValidation_ProdV2.csv"

# Thresholds for different types of fields
CONTENT_SIMILARITY_THRESHOLD = 0.95  # More lenient for content
METADATA_SIMILARITY_THRESHOLD = 0.98  # Stricter for metadata fields
EXACT_MATCH_FIELDS = {'categoryName', 'timeDuration'}  # Fields requiring exact matches

def normalize_text(text):
    """Enhanced text normalization"""
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'\W+', ' ', text)  # Remove non-word characters
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text

def calculate_field_similarity(text1, text2, field_name):
    """Calculate similarity between two fields using appropriate method"""
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
        
    # For very short texts, use sequence matcher
    if len(text1) < 50 and len(text2) < 50:
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    # For longer texts, use TF-IDF
    vectorizer = TfidfVectorizer()
    try:
        tfidf = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(tfidf[0], tfidf[1])[0][0]
    except:
        # Fallback to sequence matcher if TF-IDF fails
        return difflib.SequenceMatcher(None, text1, text2).ratio()

def generate_field_diff(text1, text2, field_name):
    """Generate detailed diff for field mismatches"""
    differ = difflib.HtmlDiff(wrapcolumn=60)
    return differ.make_table(
        text1.splitlines(), 
        text2.splitlines(),
        context=True,
        numlines=2,
        fromdesc=f'Contentful {field_name}',
        todesc=f'Strapi {field_name}'
    )

def load_data(file_path, fields):
    """Load data with enhanced error handling and validation"""
    data = defaultdict(dict)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                link = row['linkUrl'].strip()
                for field in fields:
                    data[link][field] = normalize_text(row.get(field, ''))
            except KeyError as e:
                print(f"Missing expected field {e} in row: {row}")
    return data

# Field mappings between systems
CONTENTFUL_FIELDS = ['title', 'metaTitle', 'metaDescription', 'categoryName', 
                    'timeDuration', 'content']
STRAPI_FIELDS = ['title', 'metaTitle', 'metaDescription', 'categoryName',
                'timeDuration', 'strapi_content']

# Field mappings for comparison
FIELD_MAPPINGS = {
    'content': 'strapi_content',
    'title': 'title',
    'metaTitle': 'metaTitle',
    'metaDescription': 'metaDescription',
    'categoryName': 'categoryName',
    'timeDuration': 'timeDuration'
}

# Load datasets
contentful_data = load_data(CONTENTFUL_CSV, CONTENTFUL_FIELDS)
strapi_data = load_data(STRAPI_CSV, STRAPI_FIELDS)

# Find all unique URLs
all_urls = set(contentful_data.keys()).union(set(strapi_data.keys()))

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    headers = [
        'linkUrl', 'status', 'field_similarities', 'field_mismatches',
        'missing_in_strapi', 'missing_in_contentful', 'detailed_diffs'
    ]
    writer.writerow(headers)

    for url in all_urls:
        row_data = {
            'linkUrl': url,
            'status': '✅ Valid',
            'field_similarities': {},
            'field_mismatches': [],
            'missing_in_strapi': '❌' if url not in strapi_data else '',
            'missing_in_contentful': '❌' if url not in contentful_data else '',
            'detailed_diffs': {}
        }

        # Check for existence in both systems
        if not strapi_data.get(url) or not contentful_data.get(url):
            row_data['status'] = '❌ Missing'
            writer.writerow([
                row_data['linkUrl'],
                row_data['status'],
                '',
                '',
                row_data['missing_in_strapi'],
                row_data['missing_in_contentful'],
                ''
            ])
            continue

        # Compare all fields
        for contentful_field, strapi_field in FIELD_MAPPINGS.items():
            c_value = contentful_data[url].get(contentful_field, '')
            s_value = strapi_data[url].get(strapi_field, '')

            if contentful_field in EXACT_MATCH_FIELDS:
                # Exact match check
                similarity = 1.0 if c_value == s_value else 0.0
                if similarity < 1.0:
                    row_data['field_mismatches'].append(
                        f"{contentful_field} (Exact match required)"
                    )
            else:
                # Calculate similarity based on field type
                similarity = calculate_field_similarity(c_value, s_value, contentful_field)
                threshold = (CONTENT_SIMILARITY_THRESHOLD 
                           if contentful_field == 'content' 
                           else METADATA_SIMILARITY_THRESHOLD)
                
                if similarity < threshold:
                    row_data['field_mismatches'].append(
                        f"{contentful_field} (Similarity: {similarity:.2f})"
                    )
                    row_data['detailed_diffs'][contentful_field] = generate_field_diff(
                        c_value, s_value, contentful_field
                    )

            row_data['field_similarities'][contentful_field] = round(similarity, 3)

        # Update final status
        if row_data['field_mismatches']:
            row_data['status'] = '❌ Mismatch'

        # Write row to CSV
        writer.writerow([
            row_data['linkUrl'],
            row_data['status'],
            '; '.join([f"{k}: {v}" for k, v in row_data['field_similarities'].items()]),
            '; '.join(row_data['field_mismatches']),
            row_data['missing_in_strapi'],
            row_data['missing_in_contentful'],
            '\n'.join([f"{k}:\n{v}" for k, v in row_data['detailed_diffs'].items()])
        ])

print(f"Enhanced validation complete! Results saved to {OUTPUT_CSV}")