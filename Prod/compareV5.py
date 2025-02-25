import csv
import difflib
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# Configuration
CONTENTFUL_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/updateextracted_contentful_data.csv"
STRAPI_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/new_Strapi_prod.csv"
OUTPUT_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/comparev5_detailed.csv"

# Thresholds for similarity
CONTENT_SIMILARITY_THRESHOLD = 0.95
METADATA_SIMILARITY_THRESHOLD = 0.98
EXACT_MATCH_FIELDS = {'categoryName', 'timeDuration'}
BOOLEAN_FIELDS = {'isThisAPrimaryArticle', 'isThisAFeaturedArticle'}

BOOLEAN_MAPPING = {"yes": "true", "no": "false"}

def normalize_text(text):
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'[^a-zA-Z0-9 ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return BOOLEAN_MAPPING.get(text, text)

def calculate_field_similarity(text1, text2):
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
    
    if len(text1) < 50 and len(text2) < 50:
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    vectorizer = TfidfVectorizer()
    try:
        tfidf = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(tfidf[0], tfidf[1])[0][0]
    except:
        return difflib.SequenceMatcher(None, text1, text2).ratio()

def load_data(file_path, fields):
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

CONTENTFUL_FIELDS = ['contentfulId', 'title', 'metaTitle', 'metaDescription', 'linkText', 
                    'categoryName', 'timeDuration', 'content']
STRAPI_FIELDS = ['contentfulId', 'title', 'metaTitle', 'metaDescription', 'linkText', 
                 'categoryName', 'timeDuration', 'strapi_content']

FIELD_MAPPINGS = {
    'content': 'strapi_content',
    'title': 'title',
    'metaTitle': 'metaTitle',
    'metaDescription': 'metaDescription',
    'categoryName': 'categoryName',
    'timeDuration': 'timeDuration',
    'linkText': 'linkText',
    'contentfulId': 'contentfulId'
}

# Load data
contentful_data = load_data(CONTENTFUL_CSV, CONTENTFUL_FIELDS)
strapi_data = load_data(STRAPI_CSV, STRAPI_FIELDS)
all_urls = set(contentful_data.keys()).union(set(strapi_data.keys()))

# Prepare data for reporting
results = []
for url in all_urls:
    row = {'linkUrl': url}
    for contentful_field, strapi_field in FIELD_MAPPINGS.items():
        c_value = contentful_data.get(url, {}).get(contentful_field, 'MISSING')
        s_value = strapi_data.get(url, {}).get(strapi_field, 'MISSING')

        # Skip if both values are empty or missing
        if (c_value in ['n a', '', 'MISSING']) and (s_value in ['n a', '', 'MISSING']):
            continue
            
        # Calculate similarity
        similarity = 'MISSING' if (c_value == 'MISSING' or s_value == 'MISSING') else round(calculate_field_similarity(c_value, s_value), 3)
        
        # Determine match status
        if similarity == 'MISSING':
            status = 'MISSING'
        elif similarity >= (CONTENT_SIMILARITY_THRESHOLD if contentful_field == 'content' else METADATA_SIMILARITY_THRESHOLD):
            status = 'MATCH'
        else:
            status = 'MISMATCH'
            
        # Add to row
        row[f'{contentful_field}_contentful'] = c_value
        row[f'{contentful_field}_strapi'] = s_value
        row[f'{contentful_field}_similarity'] = similarity
        row[f'{contentful_field}_status'] = status
    
    if len(row) > 1:  # Only add rows with actual comparisons
        results.append(row)

# Convert to DataFrame for better organization
df = pd.DataFrame(results)

# Define column order
base_fields = ['linkUrl']
content_fields = sorted([f for f in FIELD_MAPPINGS.keys() if f != 'linkUrl'])
ordered_columns = base_fields + [item for field in content_fields for item in [
    f'{field}_contentful',
    f'{field}_strapi',
    f'{field}_similarity',
    f'{field}_status'
]]

# Reorder columns and write to CSV
df = df[ordered_columns]
df.to_csv(OUTPUT_CSV, index=False)

# Generate summary statistics
total_comparisons = len(df)
mismatches = len(df[df.apply(lambda row: 'MISMATCH' in row.values, axis=1)])
missing = len(df[df.apply(lambda row: 'MISSING' in row.values, axis=1)])
match_rate = ((total_comparisons - mismatches - missing) / total_comparisons * 100) if total_comparisons > 0 else 0

# Print beautiful summary
print("\n" + "="*50)
print("DATA VALIDATION REPORT".center(50))
print("="*50)
print(f"Total URLs Compared: {total_comparisons}")
print(f"Perfect Matches: {total_comparisons - mismatches - missing}")
print(f"Mismatches Found: {mismatches}")
print(f"Missing Data Points: {missing}")
print(f"Overall Match Rate: {match_rate:.2f}%")
print("="*50)
print(f"Detailed results saved to: {OUTPUT_CSV}")
print("="*50)