import csv
import difflib
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configuration
CONTENTFUL_CSV = "Legal/data/content_extracted_data.csv"
STRAPI_CSV = "Legal/data/strapi_extracted_data.csv"
OUTPUT_CSV = "Legal/data/Match.csv"

# Thresholds for similarity
CONTENT_SIMILARITY_THRESHOLD = 0.95
METADATA_SIMILARITY_THRESHOLD = 0.98

BOOLEAN_MAPPING = {"yes": "true", "no": "false"}

def normalize_text(text):
    """Cleans and normalizes text for comparison."""
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'[^a-zA-Z0-9 ]+', ' ', text)  # Remove special characters
    text = re.sub(r'\s+', ' ', text).strip().lower()  # Convert to lowercase
    return BOOLEAN_MAPPING.get(text, text)

def clean_title(title):
    """Removes special characters and converts title to lowercase for better matching."""
    if not isinstance(title, str):
        return "unknown"
    return re.sub(r'[^a-zA-Z0-9]', '', title).strip().lower()  # Remove special chars & spaces

def calculate_field_similarity(text1, text2):
    if not text1 and not text2:
        return 1.0  # Both missing = perfect match
    if not text1 or not text2:
        return 0.0  # One missing, no similarity
    
    if len(text1) < 50 and len(text2) < 50:
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    vectorizer = TfidfVectorizer()
    try:
        tfidf = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(tfidf[0], tfidf[1])[0][0]
    except:
        return difflib.SequenceMatcher(None, text1, text2).ratio()

def load_data(file_path, fields):
    """Loads CSV data into a dictionary for comparison."""
    data = defaultdict(dict)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                title_key = clean_title(row.get('Title', ''))
                if not title_key:
                    continue  # Skip if no Title is available
                
                for field in fields:
                    data[title_key][field] = normalize_text(row.get(field, ''))
            except KeyError as e:
                print(f"Missing expected field {e} in row: {row}")
    return data

# Fields for comparison
FIELDS_TO_COMPARE = ['Title', 'Name', 'Meta Title', 'Meta Description', 'Canonical', 'Mapping Name', 'Content Menu', 'Content']

# Load data from CSVs (using cleaned Title as the key)
contentful_data = load_data(CONTENTFUL_CSV, FIELDS_TO_COMPARE)
strapi_data = load_data(STRAPI_CSV, FIELDS_TO_COMPARE)

# Get unique Titles for comparison
all_titles = set(contentful_data.keys()).union(set(strapi_data.keys()))

# Write results to CSV
with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    headers = ['Title', 'Field', 'Contentful Value', 'Strapi Value', 'Similarity']
    writer.writerow(headers)

    for title in all_titles:
        for field in FIELDS_TO_COMPARE:
            c_value = contentful_data.get(title, {}).get(field, 'MISSING')
            s_value = strapi_data.get(title, {}).get(field, 'MISSING')

            # Skip unnecessary comparisons
            if c_value in {'MISSING', 'n a', '', None} and s_value in {'MISSING', 'n a', '', None}:
                continue  

            if c_value == 'MISSING' or s_value == 'MISSING':
                similarity = 'MISSING'
            else:
                similarity = round(calculate_field_similarity(c_value, s_value), 3)

            # Only save mismatched or missing values
            if similarity != 1.0:
                writer.writerow([title, field, c_value, s_value, similarity])

print(f"✅ Validation complete! Results saved to {OUTPUT_CSV}")
