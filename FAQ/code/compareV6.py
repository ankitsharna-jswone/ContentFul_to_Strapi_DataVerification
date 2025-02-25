import pandas as pd

def compare_faq_content(contentful_file='extracted_faqs.csv',
                       strapi_file='extracted_strapi_faqs.csv',
                       output_missing='result/missing_report.csv',
                       output_mismatch='result/new_content_mismatches_report.csv'):
    stats = {
        'contentful_entries': 0,
        'strapi_entries': 0,
        'common_slugs': 0,
        'mismatches': 0,
        'missing_total': 0
    }
    
    print("Starting FAQ content comparison...")
    
    try:
        print("Loading CSV files...")
        df_contentful = pd.read_csv(contentful_file)
        df_strapi = pd.read_csv(strapi_file)
        
        stats['contentful_entries'] = len(df_contentful)
        stats['strapi_entries'] = len(df_strapi)
        
        df_contentful.set_index('Slug', inplace=True)
        df_strapi.set_index('Slug', inplace=True)
        
        columns_to_compare = ['Title', 'Description', 'Meta Title', 'Meta Description']
        
        print("Analyzing missing slugs...")
        missing_in_strapi = df_contentful.index.difference(df_strapi.index).tolist()
        missing_in_contentful = df_strapi.index.difference(df_contentful.index).tolist()
        
        missing_slugs_df = pd.DataFrame({
            'Slug': missing_in_strapi + missing_in_contentful,
            'Missing In': ['Strapi'] * len(missing_in_strapi) + ['Contentful'] * len(missing_in_contentful)
        })
        stats['missing_total'] = len(missing_slugs_df)
        
        print("Comparing content between files...")
        common_slugs = df_contentful.index.intersection(df_strapi.index)
        stats['common_slugs'] = len(common_slugs)
        
        mismatch_data = []
        for slug in common_slugs:
            row_contentful = df_contentful.loc[slug]
            row_strapi = df_strapi.loc[slug]
            
            row_result = {'Slug': slug}
            
            for col in columns_to_compare:
                val_contentful = str(row_contentful[col]).strip() if pd.notna(row_contentful[col]) else ""
                val_strapi = str(row_strapi[col]).strip() if pd.notna(row_strapi[col]) else ""
                
                row_result[col] = '✅' if val_contentful == val_strapi else '❌'
                
            mismatch_data.append(row_result)
        
        mismatch_df = pd.DataFrame(mismatch_data)
        stats['mismatches'] = len(mismatch_df[mismatch_df.eq('❌').any(axis=1)])
        
        print("Saving results...")
        missing_slugs_df.to_csv(output_missing, index=False)
        if not mismatch_df.empty:
            mismatch_df.to_csv(output_mismatch, index=False)
        
        print("\n" + "="*50)
        print(" FAQ Content Comparison Report ")
        print("="*50)
        print(f"Contentful Total Entries: {stats['contentful_entries']}")
        print(f"Strapi Total Entries: {stats['strapi_entries']}")
        print(f"Common Slugs: {stats['common_slugs']}")
        print(f"\nMissing Entries: {stats['missing_total']}")
        print(f"  - Missing in Strapi: {len(missing_in_strapi)}")
        print(f"  - Missing in Contentful: {len(missing_in_contentful)}")
        print(f"\nContent Mismatches Found: {stats['mismatches']}")
        
        if stats['mismatches'] > 0:
            print("\nMismatch Summary Table:")
            print(mismatch_df.set_index('Slug').to_string())
        
        print("\nOutput Files:")
        print(f"  - Missing Slugs: {output_missing}")
        print(f"  - Content Mismatches: {output_mismatch if not mismatch_df.empty else 'No mismatches found'}")
        
        print("\nComparison completed successfully!")
        
    except FileNotFoundError as e:
        print(f"Error: Could not find file - {str(e)}")
    except Exception as e:
        print(f"Error: An unexpected error occurred - {str(e)}")

if __name__ == "__main__":
    compare_faq_content()
