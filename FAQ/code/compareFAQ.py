import pandas as pd

# Load the CSV files
df1 = pd.read_csv('FAQ/extracted_faqs.csv')
df2 = pd.read_csv('FAQ/extracted_strapi_faqs.csv')

# Set 'Slug' as the index for both DataFrames
df1.set_index('Slug', inplace=True)
df2.set_index('Slug', inplace=True)

# Columns to compare (excluding 'Id' and 'Slug')
columns_to_compare = ['Title', 'Description', 'Meta Title', 'Meta Description']

# Find slugs missing in either file
only_in_df1 = df1.index.difference(df2.index).tolist()
only_in_df2 = df2.index.difference(df1.index).tolist()

# Create a DataFrame for missing slugs
missing_slugs_df = pd.DataFrame({
    'Slug': only_in_df1 + only_in_df2,
    'Missing In': ['extracted_strapi_faqs.csv'] * len(only_in_df1) + ['extracted_faqs.csv'] * len(only_in_df2)
})

# Compare common slugs for column mismatches
common_slugs = df1.index.intersection(df2.index)
mismatches = []

for slug in common_slugs:
    row1 = df1.loc[slug]
    row2 = df2.loc[slug]
    for col in columns_to_compare:
        val1 = row1[col]
        val2 = row2[col]
        # Check for NaN or string differences
        if pd.isna(val1) and pd.isna(val2):
            continue
        elif (val1 != val2) and (str(val1).strip() != str(val2).strip()):
            mismatches.append({
                'Slug': slug,
                'Column': col,
                'extracted_faqs.csv': val1,
                'extracted_strapi_faqs.csv': val2
            })

# Convert mismatches to DataFrame
mismatch_df = pd.DataFrame(mismatches)

# Save the results to CSV files
missing_slugs_df.to_csv('missing_slugs_report.csv', index=False)
mismatch_df.to_csv('content_mismatches_report.csv', index=False)

print("===== Report Generation Complete =====")
print("1. Missing Slugs Report saved as 'missing_slugs_report.csv'")
print("2. Content Mismatches Report saved as 'content_mismatches_report.csv'")