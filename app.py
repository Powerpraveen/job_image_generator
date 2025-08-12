import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO
import re
from datetime import datetime
import random

def get_job_details(url):
    """
    Fetches and parses job details with the most advanced and flexible date parsing.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator="\n", strip=True)

        # 1. Job Post Title
        title_element = soup.find('h1', class_='entry-title')
        title = title_element.text.strip() if title_element else "Title Not Found"

        # 2. Post Names
        post_names_text = "Check Notification"
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 1 and 'post name' in cells[0].get_text(strip=True).lower():
                post_names_text = cells[1].get_text(strip=True)
                break

        # 3. Age Limit (Focus on Max Age)
        age_limit_str = "Not Found"
        age_range_match = re.search(r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*years', page_text, re.IGNORECASE)
        if age_range_match:
            age_limit_str = f"Up to {age_range_match.group(2)} Years"
        else:
            max_age_match = re.search(r'max(?:imum)?\s*age\s*(?:limit)?\s*[:\s]*(\d{1,2})', page_text, re.IGNORECASE)
            if max_age_match:
                age_limit_str = f"Up to {max_age_match.group(1)} Years"

        # 4. Salary
        salary_str = "Not Found"
        salaries = re.findall(r'₹?\s*([\d,]{4,})', page_text)
        numeric_salaries = [int(s.replace(',', '')) for s in salaries if s.replace(',', '').isdigit()]
        if numeric_salaries:
            salary_str = f"Up to ₹{max(numeric_salaries):,}/-"

        # --- NEW: Truly Flexible Last Date Extraction ---
        last_date_str = "Not Found"
        parsed_dates = []
        
        # Pattern 1: "22 August 2025" or "22 Aug 2025"
        date_pattern1 = re.compile(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', re.IGNORECASE)
        # Pattern 2: "dd/mm/yyyy" or "dd-mm-yy"
        date_pattern2 = re.compile(r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})')

        # Find all possible date strings near keywords
        keyword_pattern = re.compile(r'(Last Date|Closing Date|Apply Before)', re.IGNORECASE)
        text_lines = page_text.split('\n')
        for i, line in enumerate(text_lines):
            if keyword_pattern.search(line):
                # Search in the same line and the next few lines for a date
                search_area = " ".join(text_lines[i:i+2])
                
                # Try Pattern 1
                for match in date_pattern1.finditer(search_area):
                    day, month_str, year = match.groups()
                    month = datetime.strptime(month_str, "%b" if len(month_str) == 3 else "%B").month
                    parsed_dates.append(datetime(int(year), month, int(day)))
                
                # Try Pattern 2
                for match in date_pattern2.finditer(search_area):
                    d, m, y = match.groups()
                    year = int(y) if len(y) == 4 else int(f"20{y}") # Convert '25' to 2025
                    if year > 2020: # Basic validation
                        parsed_dates.append(datetime(year, int(m), int(d)))

        if parsed_dates:
            last_date_str = max(parsed_dates).strftime('%d %B %Y')

        # 6. Selection Process
        selection_process_text = "As per rules"
        selection_header = soup.find(['strong', 'h3'], string=re.compile("Selection Process", re.I))
        if selection_header:
            next_element = selection_header.find_next(['ul', 'p'])
            if next_element:
                selection_process_text = ', '.join([li.get_text(strip=True) for li in next_element.find_all('li')]) if next_element.name == 'ul' else next_element.get_text(strip=True)

        details = {
            "Job Post Title": title,
            "Post Names": post_names_text,
            "Age Limit": age_limit_str,
            "Salary": salary_str,
            "Selection Process": selection_process_text,
            "Last Date": last_date_str
        }
        return details

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch URL: {e}")
        return None

def create_job_post_image(details):
    # This function remains unchanged.
    if not details: return None
    palettes = [{"bg": (34, 40, 49), "text": (238, 238, 238), "accent": (0, 173, 181)}, {"bg": (245, 245, 245), "text": (40, 40, 40), "accent": (26, 140, 140)}, {"bg": (230, 240, 255), "text": (50, 60, 80), "accent": (0, 102, 204)}]
    palette = random.choice(palettes)
    BG_COLOR, TEXT_COLOR, ACCENT_COLOR = palette["bg"], palette["text"], palette["accent"]
    keywords = ["JOB", "APPLY", "LINK", "DETAILS", "POST", "INFO"]
    cta_templates = ["Comment '{keyword}' to get the link!", "Want the link? Type '{keyword}' below!", "For application link, comment '{keyword}'."]
    width, height = 1080, 1920
    img = Image.new('RGB', (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)
    try:
        font_bold = ImageFont.truetype("Poppins-Bold.ttf", size=75); font_regular = ImageFont.truetype("Poppins-Regular.ttf", size=48); font_small = ImageFont.truetype("Poppins-Regular.ttf", size=42); header_font = ImageFont.truetype("Poppins-Bold.ttf", size=55)
    except IOError:
        st.error("Font files are missing!"); return None
    draw.rectangle([0, 0, width, 180], fill=ACCENT_COLOR); draw.text((width/2, 90), "Latest Job Update", font=header_font, fill=BG_COLOR, anchor="mm")
    y_position = 280
    wrapped_title = textwrap.wrap(details["Job Post Title"], width=25)
    for line in wrapped_title:
        draw.text((width/2, y_position), line, font=font_bold, fill=TEXT_COLOR, anchor="ms"); y_position += 80
    y_position += 60
    detail_items = {k: v for k, v in details.items() if k not in ["Job Post Title", "Last Date"]}
    for key, value in detail_items.items():
        draw.text((80, y_position), f"{key}:", font=font_small, fill=ACCENT_COLOR)
        value_y = y_position + 55
        wrapped_value = textwrap.wrap(str(value), width=38)
        for line in wrapped_value:
            draw.text((80, value_y), line, font=font_regular, fill=TEXT_COLOR); value_y += 55
        y_position = value_y + 25
    draw.rectangle([50, y_position, width - 50, y_position + 180], fill=ACCENT_COLOR)
    draw.text((width/2, y_position + 60), "Last Date to Apply", font=font_small, fill=BG_COLOR, anchor="ms")
    draw.text((width/2, y_position + 125), details["Last Date"], font=font_bold, fill=BG_COLOR, anchor="ms")
    final_cta = random.choice(cta_templates).format(keyword=random.choice(keywords))
    draw.text((width/2, height - 100), final_cta, font=font_small, fill=ACCENT_COLOR, anchor="ms")
    return img

# --- Streamlit UI (No changes needed) ---
st.set_page_config(page_title="Intelligent Job Post Generator", layout="centered")
st.title("🚀 AI Job Post Image Generator")
st.markdown("Enter a job post URL to create a unique, engaging, and professional social media image instantly.")
social_media_sizes = {"9:16 Story (1080x1920)": (1080, 1920), "Instagram Post (1080x1080)": (1080, 1080), "Facebook Post (1200x630)": (1200, 630), "Twitter Post (1024x512)": (1024, 512)}
url = st.text_input("Enter the Job Post URL:", placeholder="https://newgovtjobalert.com/...")
if st.button("Generate Image"):
    if url:
        with st.spinner("Analyzing page and creating a unique design..."):
            job_details = get_job_details(url)
            if job_details:
                generated_image = create_job_post_image(job_details)
                if generated_image:
                    st.success("Image Generated Successfully!")
                    st.image(generated_image, caption="Preview (9:16 Story)", use_column_width=True)
                    st.markdown("---"); st.subheader("Download in Any Size")
                    for name, size in social_media_sizes.items():
                        resized_img = generated_image.resize(size, Image.Resampling.LANCZOS); buf = BytesIO(); resized_img.save(buf, format="PNG")
                        st.download_button(label=f"Download {name}", data=buf.getvalue(), file_name=f"job_post_{size[0]}x{size[1]}.png", mime="image/png")
    else: st.warning("Please enter a URL to generate an image.")
