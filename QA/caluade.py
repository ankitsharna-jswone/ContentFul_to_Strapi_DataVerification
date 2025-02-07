import csv
import difflib
import re

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', str(text)).strip()
    return text.lower()

def similarity_score(text1, text2):
    return difflib.SequenceMatcher(None, clean_text(text1), clean_text(text2)).ratio()

def find_detailed_differences(text1, text2):
    text1_sentences = clean_text(text1).split(". ")
    text2_sentences = clean_text(text2).split(". ")
    
    diff = difflib.ndiff(text1_sentences, text2_sentences)
    differences = []
    
    line_num = 1
    for sentence in diff:
        if sentence.startswith('- '):
            differences.append(f"❌ Line {line_num}: Missing in Strapi → {sentence[2:]}")
        elif sentence.startswith('+ '):
            differences.append(f"➕ Line {line_num}: Extra in Strapi → {sentence[2:]}")
        
        if not sentence.startswith('  '):  # Count only differences
            line_num += 1
            
    return '\n'.join(differences) if differences else "No significant differences"

def load_contentful_data(file_path):
    contentful_data = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            link = row['linkUrl'].strip()
            if link:
                contentful_data[link] = {
                    'title': row['title'].strip(),
                    'metaTitle': row['metaTitle'].strip(),
                    'metaDescription': row['metaDescription'].strip(),
                    'categoryName': row['categoryName'].strip(),
                    'timeDuration': row['timeDuration'].strip() if 'timeDuration' in row else '',
                    'content': row['content'].strip() if 'content' in row else ''
                }
    return contentful_data

def load_strapi_data(file_path):
    strapi_data = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            link = row['linkUrl'].strip()
            if link and link.lower() != 'all':  # Exclude the 'all' entry
                strapi_data[link] = {
                    'title': row['title'].strip(),
                    'metaTitle': row['metaTitle'].strip(),
                    'metaDescription': row['metaDescription'].strip(),
                    'categoryName': row['categoryName'].strip(),
                    'timeDuration': row['timeDuration'].strip() if 'timeDuration' in row else '',
                    'content': row['strapi_content'].strip() if 'strapi_content' in row else ''
                }
    return strapi_data

def main():
    # File paths
    contentful_csv = 'QA/blogs_data.csv'
    strapi_csv = 'QA/strapi_extracted_data.csv'
    output_csv = 'validation_report.csv'
    
    # Load data
    print("Loading Contentful data...")
    contentful_data = load_contentful_data(contentful_csv)
    print("Loading Strapi data...")
    strapi_data = load_strapi_data(strapi_csv)
    
    # Generate report
    print("Generating validation report...")
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'Link URL',
            'Overall Status',
            'Similarity Score',
            'Title Match',
            'Meta Title Match',
            'Meta Description Match',
            'Category Match',
            'Time Duration Match',
            'Content Match',
            'Detailed Differences'
        ])
        
        # Process each entry
        all_links = set(contentful_data.keys()) | set(strapi_data.keys())
        for link in all_links:
            if link not in strapi_data:
                writer.writerow([
                    link,
                    '❌ Missing in Strapi',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'Entry not found in Strapi'
                ])
                continue
                
            if link not in contentful_data:
                writer.writerow([
                    link,
                    '❌ Missing in Contentful',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'N/A',
                    'Entry not found in Contentful'
                ])
                continue
            
            # Compare fields
            contentful_entry = contentful_data[link]
            strapi_entry = strapi_data[link]
            
            field_scores = {
                'title': similarity_score(contentful_entry['title'], strapi_entry['title']),
                'metaTitle': similarity_score(contentful_entry['metaTitle'], strapi_entry['metaTitle']),
                'metaDescription': similarity_score(contentful_entry['metaDescription'], strapi_entry['metaDescription']),
                'categoryName': similarity_score(contentful_entry['categoryName'], strapi_entry['categoryName']),
                'timeDuration': similarity_score(contentful_entry['timeDuration'], strapi_entry['timeDuration']),
                'content': similarity_score(contentful_entry['content'], strapi_entry['content'])
            }
            
            # Determine match status for each field
            field_status = {
                field: '✅ Match' if score == 1.0 else '⚠️ Partial' if score > 0.85 else '❌ Mismatch'
                for field, score in field_scores.items()
            }
            
            # Calculate overall similarity score
            overall_score = sum(field_scores.values()) / len(field_scores)
            
            # Determine overall status
            if all(status == '✅ Match' for status in field_status.values()):
                overall_status = '✅ Perfect Match'
            elif any(status == '❌ Mismatch' for status in field_status.values()):
                overall_status = '❌ Mismatch'
            else:
                overall_status = '⚠️ Partial Match'
            
            # Get detailed content differences
            differences = find_detailed_differences(contentful_entry['content'], strapi_entry['content'])
            
            writer.writerow([
                link,
                overall_status,
                f"{overall_score:.2f}",
                field_status['title'],
                field_status['metaTitle'],
                field_status['metaDescription'],
                field_status['categoryName'],
                field_status['timeDuration'],
                field_status['content'],
                differences
            ])
    
    print(f"✅ Validation complete! Report saved as {output_csv}")

if __name__ == '__main__':
    main()