import requests
import json
import csv
import time
from bs4 import BeautifulSoup

# Strapi API Base URL
STRAPI_API_BASE_URL = "https://qa-cms.msme.jswone.in/api/jsw-blogs-articless"

# API Headers
STRAPI_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://qa-ssr.msme.jswone.in",
    "referer": "https://qa-ssr.msme.jswone.in/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
}

# Load Contentful Blog Links
contentful_file_path = "QA/resut.json"
with open(contentful_file_path, "r", encoding="utf-8") as file:
    contentful_data = json.load(file)

# Extract linkUrls
blog_links = [
    blog["fields"].get("linkUrl", "").strip() 
    for blog in contentful_data.get("items", []) 
    if blog["fields"].get("linkUrl")
]

# Function to Clean HTML Content
def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()

# Output CSV File
output_csv = "strapi_extracted_data.csv"

# Define CSV Headers
fields = [
    "linkUrl", "title", "metaTitle", "metaDescription", "categoryName", 
    "timeDuration", "createdAt", "updatedAt", "publishedAt", "strapi_content"
]

# Write CSV Data
with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(fields)  # Write header row

    for link in blog_links:
        strapi_url = f"{STRAPI_API_BASE_URL}?filters[linkUrl][$eq]={link}&populate[detailInfo][populate]=*"

        try:
            response = requests.get(strapi_url, headers=STRAPI_HEADERS, timeout=10)
            if response.status_code == 200:
                strapi_data = response.json()

                # Extract the first matching data entry
                blog_entry = strapi_data.get("data", [{}])[0].get("attributes", {})

                # Extract required fields
                title = blog_entry.get("title", "N/A")
                meta_title = blog_entry.get("metaTitle", "N/A")
                meta_desc = blog_entry.get("metaDescription", "N/A")
                category = blog_entry.get("categoryName", "N/A")
                time_duration = blog_entry.get("timeDuration", "N/A")
                created_at = blog_entry.get("createdAt", "N/A")
                updated_at = blog_entry.get("updatedAt", "N/A")
                published_at = blog_entry.get("publishedAt", "N/A")

                # Extract and clean the content
                content_blocks = blog_entry.get("detailInfo", [])
                strapi_text = " ".join(clean_html(block.get("content", "")) for block in content_blocks)

                # Write data row
                writer.writerow([
                    link, title, meta_title, meta_desc, category, 
                    time_duration, created_at, updated_at, published_at, strapi_text
                ])
                
                print(f"✅ Extracted content for: {link}")

            else:
                print(f"❌ Failed to fetch {link} - HTTP {response.status_code}")

        except requests.RequestException as e:
            print(f"⚠️ Error fetching {link}: {e}")

        time.sleep(1)  # Prevents excessive API calls

print(f"✅ Strapi data extraction complete! Results saved in {output_csv}")
