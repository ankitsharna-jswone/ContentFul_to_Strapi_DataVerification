import pandas as pd

# Load the CSV files
df_contentful = pd.read_csv('FAQ/Data/extracted_faqs.csv')  # Contentful data
df_strapi = pd.read_csv('FAQ/Data/extracted_strapi_faqs.csv')  # Strapi data

# Set 'Slug' as the index for both DataFrames
df_contentful.set_index('Slug', inplace=True)
df_strapi.set_index('Slug', inplace=True)

# Columns to compare (excluding 'Id' and 'Slug')
columns_to_compare = ['Title', 'Description', 'Meta Title', 'Meta Description']

# Function to compare two DataFrames and find mismatches
def compare_dataframes(df1, df2, df1_name, df2_name):
    mismatches = []
    common_slugs = df1.index.intersection(df2.index)
    
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
                    df1_name: val1,
                    df2_name: val2
                })
    
    return mismatches

# Find slugs missing in either file
missing_in_strapi = df_contentful.index.difference(df_strapi.index).tolist()
missing_in_contentful = df_strapi.index.difference(df_contentful.index).tolist()

# Create a DataFrame for missing slugs
missing_slugs_df = pd.DataFrame({
    'Slug': missing_in_strapi + missing_in_contentful,
    'Missing In': ['Strapi'] * len(missing_in_strapi) + ['Contentful'] * len(missing_in_contentful)
})

# Compare Contentful to Strapi
contentful_to_strapi_mismatches = compare_dataframes(df_contentful, df_strapi, 'Contentful', 'Strapi')

# Compare Strapi to Contentful
strapi_to_contentful_mismatches = compare_dataframes(df_strapi, df_contentful, 'Strapi', 'Contentful')

# Combine mismatches from both directions
all_mismatches = contentful_to_strapi_mismatches + strapi_to_contentful_mismatches

# Convert mismatches to DataFrame
mismatch_df = pd.DataFrame(all_mismatches)

# Save the results to CSV files
missing_slugs_df.to_csv('FAQ/result/missing_report.csv', index=False)
mismatch_df.to_csv('FAQ/result/content_mismatches_report.csv', index=False)

print("===== Two-Sided Validation Report Generation Complete =====")
print("1. Missing Slugs Report saved as 'missing_slugs_report.csv'")
print("2. Content Mismatches Report saved as 'content_mismatches_report.csv'")


