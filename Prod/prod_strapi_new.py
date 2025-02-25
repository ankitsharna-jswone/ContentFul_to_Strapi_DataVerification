import requests
import json
import csv
import time
from bs4 import BeautifulSoup

# Strapi API Base URL
STRAPI_API_BASE_URL = "https://cms.jswonemsme.com/api/jsw-blogs-articless"

# API Headers
STRAPI_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://qa-ssr.msme.jswone.in",
    "referer": "https://qa-ssr.msme.jswone.in/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
}

# Load Contentful Blog Links
contentful_file_path = "/Users/ankitsharma/Desktop/DataValidation/Prod/data/content.json"

with open(contentful_file_path, "r", encoding="utf-8") as file:
    contentful_data = json.load(file)

# Extract `linkUrl` values dynamically
blog_links = []
for blog in contentful_data.get("items", []):
    link_data = blog.get("fields", {}).get("linkUrl", {})

    # Fix: Extract `en-US` key safely
    if isinstance(link_data, dict) and "en-US" in link_data:
        blog_links.append(link_data["en-US"].strip())  # Extract the actual string
    else:
        print(f"⚠️ Skipping invalid linkUrl format: {link_data}")  # Debugging

# Function to clean HTML content
def clean_html(raw_html):
    """Removes HTML tags and extracts clean text."""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

# Output CSV File
output_csv = "/Users/ankitsharma/Desktop/DataValidation/Prod/csv/new_Strapi_prod.csv"

# Define CSV Headers (Including new fields)
fields = [
    "linkUrl", "title", "metaTitle", "metaDescription", "categoryName", 
    "timeDuration", "createdAt", "updatedAt", "publishedAt", "linkText", 
    "isThisAFeaturedArticle", "isThisAPrimaryArticle", "isMsmeArticle", "isSellerArticle", 
    "contentfulId", "strapi_content"
]

# Write CSV Data
with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(fields)  # Write header row

    for link in blog_links:
        # Construct the API URL dynamically with `linkUrl`
        strapi_url = (
            f"{STRAPI_API_BASE_URL}?filters%5BlinkUrl%5D%5B%24eq%5D={link}"
            f"&populate%5BdetailInfo%5D%5Bpopulate%5D=%2A"
            f"&populate%5Bmedia%5D%5Bpopulate%5D=%2A"
            f"&populate%5Bthumbnail%5D%5Bpopulate%5D=%2A"
        )

        try:
            response = requests.get(strapi_url, headers=STRAPI_HEADERS, timeout=10)
            if response.status_code == 200:
                strapi_data = response.json()
                blog_entries = strapi_data.get("data", [])

                if not blog_entries:
                    print(f"⚠️ No data found for: {link}")
                    continue  # Skip this link if no data is found

                for blog_entry in blog_entries:
                    attributes = blog_entry.get("attributes", {})

                    # Extract required fields
                    title = attributes.get("title", "N/A")
                    meta_title = attributes.get("metaTitle", "N/A")
                    meta_desc = attributes.get("metaDescription", "N/A")
                    category = attributes.get("categoryName", "N/A")
                    time_duration = attributes.get("timeDuration", "N/A")
                    created_at = attributes.get("createdAt", "N/A")
                    updated_at = attributes.get("updatedAt", "N/A")
                    published_at = attributes.get("publishedAt", "N/A")
                    link_text = attributes.get("linkText", "N/A")
                    is_featured = attributes.get("isThisAFeaturedArticle", "N/A")
                    is_primary = attributes.get("isThisAPrimaryArticle", "N/A")
                    is_msme = attributes.get("isMsmeArticle", "N/A")
                    is_seller = attributes.get("isSellerArticle", "N/A")
                    contentful_id = attributes.get("contentfulId", "N/A")

                    # Extract and clean the content
                    content_blocks = attributes.get("detailInfo", [])
                    strapi_text = " ".join(clean_html(block.get("content", "")) for block in content_blocks)

                    # Write data row
                    writer.writerow([
                        link, title, meta_title, meta_desc, category, 
                        time_duration, created_at, updated_at, published_at, 
                        link_text, is_featured, is_primary, is_msme, is_seller, 
                        contentful_id, strapi_text
                    ])

                print(f"✅ Extracted content for: {link}")

            else:
                print(f"❌ Failed to fetch {link} - HTTP {response.status_code}")

        except requests.RequestException as e:
            print(f"⚠️ Error fetching {link}: {e}")

        time.sleep(1)  # Prevents excessive API calls

print(f"✅ Strapi data extraction complete! Results saved in {output_csv}")
