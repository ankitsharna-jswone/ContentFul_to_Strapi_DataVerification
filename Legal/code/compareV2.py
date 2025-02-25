import csv
import difflib
import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

# Configuration
CONTENTFUL_CSV = "data/content_extracted_data.csv"
STRAPI_CSV = "data/strapi_extracted_data.csv"
OUTPUT_CSV = "data/Match.csv"
SUMMARY_TXT = "data/Match_Summary.txt"

# Thresholds for similarity
CONTENT_SIMILARITY_THRESHOLD = 0.95
METADATA_SIMILARITY_THRESHOLD = 0.98

BOOLEAN_MAPPING = {"yes": "true", "no": "false"}

def normalize_text(text):
    """Cleans and normalizes text for comparison."""
    if not isinstance(text, str):
        text = str(text)
    text = re.sub(r'[^a-zA-Z0-9 ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return BOOLEAN_MAPPING.get(text, text)

def clean_title(title):
    """Removes special characters and converts title to lowercase for better matching."""
    if not isinstance(title, str):
        return "unknown"
    return re.sub(r'[^a-zA-Z0-9]', '', title).strip().lower()

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
    """Loads CSV data into a dictionary for comparison."""
    data = defaultdict(dict)
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                title_key = clean_title(row.get('Title', ''))
                if not title_key:
                    continue
                for field in fields:
                    data[title_key][field] = normalize_text(row.get(field, ''))
            except KeyError as e:
                print(f"Missing expected field {e} in row: {row}")
    return data

# Fields for comparison
FIELDS_TO_COMPARE = ['Title', 'Name', 'Meta Title', 'Meta Description', 'Canonical', 'Mapping Name', 'Content Menu', 'Content']

# Load data from CSVs
contentful_data = load_data(CONTENTFUL_CSV, FIELDS_TO_COMPARE)
strapi_data = load_data(STRAPI_CSV, FIELDS_TO_COMPARE)

# Get unique Titles for comparison
all_titles = set(contentful_data.keys()).union(set(strapi_data.keys()))

# Enhanced reporting data structures
mismatch_counts = defaultdict(int)
field_mismatches = defaultdict(int)
total_comparisons = 0
perfect_matches = 0
missing_data = 0
low_similarity = 0

# Prepare data for columnar output
title_data = defaultdict(dict)
for title in all_titles:
    for field in FIELDS_TO_COMPARE:
        c_value = contentful_data.get(title, {}).get(field, 'MISSING')
        s_value = strapi_data.get(title, {}).get(field, 'MISSING')
        total_comparisons += 1

        if c_value in {'MISSING', 'n a', '', None} and s_value in {'MISSING', 'n a', '', None}:
            continue  # Skip empty comparisons

        if c_value == 'MISSING' or s_value == 'MISSING':
            similarity = 'MISSING'
            status = 'Missing Data'
            missing_data += 1
        else:
            similarity = round(calculate_field_similarity(c_value, s_value), 3)
            if similarity == 1.0:
                status = 'Perfect Match'
                perfect_matches += 1
            elif similarity >= (CONTENT_SIMILARITY_THRESHOLD if field == 'Content' else METADATA_SIMILARITY_THRESHOLD):
                status = 'Near Match'
            else:
                status = 'Mismatch'
                mismatch_counts[title] += 1
                field_mismatches[field] += 1
                low_similarity += 1

        # Store data for this title and field
        title_data[title][f"{field}_Contentful"] = c_value
        title_data[title][f"{field}_Strapi"] = s_value
        title_data[title][f"{field}_Similarity"] = similarity
        title_data[title][f"{field}_Status"] = status

# Write results to CSV with columns for each field
with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    # Define headers dynamically based on fields
    headers = ['Title']
    for field in FIELDS_TO_COMPARE:
        headers.extend([f"{field}_Contentful", f"{field}_Strapi", f"{field}_Similarity", f"{field}_Status"])
    writer.writerow(headers)

    for title in sorted(all_titles):
        row = [title]
        for field in FIELDS_TO_COMPARE:
            row.extend([
                title_data[title].get(f"{field}_Contentful", 'MISSING'),
                title_data[title].get(f"{field}_Strapi", 'MISSING'),
                title_data[title].get(f"{field}_Similarity", 'MISSING'),
                title_data[title].get(f"{field}_Status", 'N/A')
            ])
        writer.writerow(row)

# Write summary report to a text file
with open(SUMMARY_TXT, 'w', encoding='utf-8') as summary_file:
    summary_file.write(f"Content Comparison Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    summary_file.write("=" * 50 + "\n\n")
    summary_file.write(f"Total Titles Compared: {len(all_titles)}\n")
    summary_file.write(f"Total Field Comparisons: {total_comparisons}\n")
    summary_file.write(f"Perfect Matches: {perfect_matches} ({(perfect_matches/total_comparisons)*100:.2f}%)\n")
    summary_file.write(f"Missing Data Instances: {missing_data} ({(missing_data/total_comparisons)*100:.2f}%)\n")
    summary_file.write(f"Low Similarity Cases: {low_similarity} ({(low_similarity/total_comparisons)*100:.2f}%)\n\n")
    
    summary_file.write("Top Titles with Most Mismatches:\n")
    for title, count in sorted(mismatch_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        summary_file.write(f" - {title}: {count} mismatches\n")
    
    summary_file.write("\nFields with Most Mismatches:\n")
    for field, count in sorted(field_mismatches.items(), key=lambda x: x[1], reverse=True):
        summary_file.write(f" - {field}: {count} mismatches\n")

print(f"✅ Validation complete!")
print(f" - Detailed results saved to {OUTPUT_CSV}")
print(f" - Summary report saved to {SUMMARY_TXT}")