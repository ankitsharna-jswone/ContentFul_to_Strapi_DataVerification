import csv
import difflib
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configuration
CONTENTFUL_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/updateextracted_contentful_data.csv"
STRAPI_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/new_Strapi_prod.csv"
OUTPUT_CSV = "/Users/ankitsharma/Desktop/DataValidation/Prod/data/compareV3.csv"

# Thresholds for similarity
CONTENT_SIMILARITY_THRESHOLD = 0.99
METADATA_SIMILARITY_THRESHOLD = 0.99
EXACT_MATCH_FIELDS = {'categoryName', 'timeDuration'}

def normalize_text(text):
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'[^a-zA-Z0-9 ]+', ' ', text)  # Remove special characters
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text

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

CONTENTFUL_FIELDS = ['title', 'metaTitle', 'metaDescription','linkText', 'categoryName', 'timeDuration', 'content','isThisAPrimaryArticle','isThisAFeaturedArticle']
STRAPI_FIELDS = ['title', 'metaTitle', 'metaDescription','linkText', 'categoryName', 'timeDuration', 'strapi_content', 'isThisAPrimaryArticle','isThisAFeaturedArticle']

FIELD_MAPPINGS = {
    'content': 'strapi_content',
    'title': 'title',
    'metaTitle': 'metaTitle',
    'metaDescription': 'metaDescription',
    'categoryName': 'categoryName',
    'timeDuration': 'timeDuration',
    'linkText' : 'linkText',
    'isThisAPrimaryArticle': 'isThisAPrimaryArticle',
    'isThisAFeaturedArticle' : 'isThisAFeaturedArticle',
    'contentfulId':'contentfulId'
    
}

contentful_data = load_data(CONTENTFUL_CSV, CONTENTFUL_FIELDS)
strapi_data = load_data(STRAPI_CSV, STRAPI_FIELDS)

all_urls = set(contentful_data.keys()).union(set(strapi_data.keys()))

with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    headers = ['linkUrl', 'field', 'contentful_value', 'strapi_value', 'similarity']
    writer.writerow(headers)

    for url in all_urls:
        for contentful_field, strapi_field in FIELD_MAPPINGS.items():
            c_value = contentful_data.get(url, {}).get(contentful_field, 'MISSING')
            s_value = strapi_data.get(url, {}).get(strapi_field, 'MISSING')

            if c_value == 'MISSING' or s_value == 'MISSING':
                similarity = 'MISSING'
            else:
                similarity = round(calculate_field_similarity(c_value, s_value), 3)
            
            if similarity != 1.0:
                writer.writerow([url, contentful_field, c_value, s_value, similarity])

print(f"Validation complete! Results saved to {OUTPUT_CSV}")
