import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO
import re
from datetime import datetime
import random

# The get_job_details function is stable and requires no changes.
def get_job_details(url):
    """
    Fetches and parses job details with advanced and flexible data parsing.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator="\n", strip=True)

        # Title
        title = soup.find('h1', class_='entry-title').text.strip() if soup.find('h1', class_='entry-title') else "Title Not Found"

        # Post Names
        post_names_text = "Check Notification"
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 1 and 'post name' in cells[0].get_text(strip=True).lower():
                post_names_text = cells[1].get_text(strip=True); break
        
        # Age Limit
        age_limit_str = "Not Found"
        age_range_match = re.search(r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*years', page_text, re.IGNORECASE)
        if age_range_match: age_limit_str = f"Up to {age_range_match.group(2)} Years"
        else:
            max_age_match = re.search(r'max(?:imum)?\s*age\s*(?:limit)?\s*[:\s]*(\d{1,2})', page_text, re.IGNORECASE)
            if max_age_match: age_limit_str = f"Up to {max_age_match.group(1)} Years"

        # Salary
        salary_str = "Not Found"
        salaries = re.findall(r'₹?\s*([\d,]{4,})', page_text)
        numeric_salaries = [int(s.replace(',', '')) for s in salaries if s.replace(',', '').isdigit()]
        if numeric_salaries: salary_str = f"Up to ₹{max(numeric_salaries):,}/-"
        
        # Last Date
        last_date_str = "Not Found"
        parsed_dates = []
        date_pattern1 = re.compile(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})', re.I)
        date_pattern2 = re.compile(r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})')
        keyword_pattern = re.compile(r'(Last Date|Closing Date|Apply Before)', re.I)
        for i, line in enumerate(page_text.split('\n')):
            if keyword_pattern.search(line):
                search_area = " ".join(page_text.split('\n')[i:i+3]) # Search 3 lines for safety
                for match in date_pattern1.finditer(search_area):
                    day, month_str, year = match.groups(); month = datetime.strptime(month_str, "%b" if len(month_str)==3 else "%B").month
                    parsed_dates.append(datetime(int(year), month, int(day)))
                for match in date_pattern2.finditer(search_area):
                    d, m, y = match.groups(); year = int(f"20{y}") if len(y)==2 else int(y)
                    if year > 2020: parsed_dates.append(datetime(year, int(m), int(d)))
        if parsed_dates: last_date_str = max(parsed_dates).strftime('%d %B %Y')

        # Selection Process
        selection_process_text = "As per rules"
        selection_header = soup.find(['strong', 'h3'], string=re.compile("Selection Process", re.I))
        if selection_header:
            next_element = selection_header.find_next(['ul', 'p'])
            if next_element: selection_process_text = ', '.join([li.get_text(strip=True) for li in next_element.find_all('li')]) if next_element.name == 'ul' else next_element.get_text(strip=True)

        return {
            "Job Post Title": title, "Post Names": post_names_text, "Age Limit": age_limit_str,
            "Salary": salary_str, "Selection Process": selection_process_text, "Last Date": last_date_str
        }
    except Exception as e:
        st.error(f"An error occurred while fetching details: {e}"); return None

# --- NEW: Re-engineered Image Generation with Anti-Trimming Layout ---
def create_job_post_image(details):
    """
    Creates a visually dynamic image with a robust layout engine to prevent text trimming.
    """
    if not details: return None

    # Color palettes and CTA keywords
    palettes = [{"bg": (34, 40, 49), "text": (238, 238, 238), "accent": (0, 173, 181)}, {"bg": (245, 245, 245), "text": (40, 40, 40), "accent": (26, 140, 140)}]
    palette = random.choice(palettes)
    BG_COLOR, TEXT_COLOR, ACCENT_COLOR = palette["bg"], palette["text"], palette["accent"]
    keywords = ["JOB", "APPLY", "LINK", "DETAILS", "POST", "INFO"]
    cta_templates = ["Comment '{keyword}' to get the link!", "Want the link? Type '{keyword}' below!"]
    
    width, height = 1080, 1920
    img = Image.new('RGB', (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_bold = ImageFont.truetype("Poppins-Bold.ttf", 68)
        font_regular = ImageFont.truetype("Poppins-Regular.ttf", 42)
        font_small = ImageFont.truetype("Poppins-Regular.ttf", 40)
        header_font = ImageFont.truetype("Poppins-Bold.ttf", 50)
    except IOError:
        st.error("Font files are missing!"); return None

    # --- Header ---
    draw.rectangle([0, 0, width, 180], fill=ACCENT_COLOR)
    draw.text((width/2, 90), "Latest Job Update", font=header_font, fill=BG_COLOR, anchor="mm")

    # --- Main Content with Robust Spacing and Margins ---
    y_position = 250 # Start position for content
    margin = 100 # WIDER safety margin to prevent trimming

    # Draw Title
    title_lines = textwrap.wrap(details["Job Post Title"], width=25) # NARROWER wrap width
    for line in title_lines:
        draw.text((width/2, y_position), line, font=font_bold, fill=TEXT_COLOR, anchor="ms")
        y_position += font_bold.getbbox(line)[3] + 15 
    y_position += 50 

    # Draw Detail Items
    detail_items = {k: v for k, v in details.items() if k not in ["Job Post Title", "Last Date"]}
    for key, value in detail_items.items():
        draw.text((margin, y_position), f"{key}:", font=font_small, fill=ACCENT_COLOR)
        y_position += font_small.getbbox(f"{key}:")[3] + 10

        value_lines = textwrap.wrap(str(value), width=40) # NARROWER wrap width
        for line in value_lines:
            draw.text((margin, y_position), line, font=font_regular, fill=TEXT_COLOR)
            y_position += font_regular.getbbox(line)[3] + 10
        y_position += 40 

    # --- Last Date Box (Positioned safely above the footer) ---
    box_height = 180
    box_y_start = height - 160 - box_height # Position it above the footer with padding
    draw.rectangle([margin, box_y_start, width - margin, box_y_start + box_height], fill=ACCENT_COLOR)
    draw.text((width/2, box_y_start + 55), "Last Date to Apply", font=font_small, fill=BG_COLOR, anchor="ms")
    draw.text((width/2, box_y_start + 125), details["Last Date"], font=font_bold, fill=BG_COLOR, anchor="ms")

    # --- FIXED FOOTER: Always Visible ---
    final_cta = random.choice(cta_templates).format(keyword=random.choice(keywords))
    footer_y = height - 80
    draw.text((width/2, footer_y), final_cta, font=font_small, fill=ACCENT_COLOR, anchor="ms")

    return img

# --- Streamlit UI (No changes needed) ---
st.set_page_config(page_title="Intelligent Job Post Generator", layout="centered")
st.title("🚀 AI Job Post Image Generator")
st.markdown("Enter a job post URL to create a unique, engaging, and professional social media image instantly.")
social_media_sizes = {"9:16 Story (1080x1920)": (1080, 1920), "Instagram Post (1080x1080)": (1080, 1080), "Facebook Post (1200x630)": (1200, 630)}
url = st.text_input("Enter the Job Post URL:", placeholder="https://newgovtjobalert.com/...")
if st.button("Generate Image"):
    if url:
        with st.spinner("Analyzing page and creating a robust design..."):
            job_details = get_job_details(url)
            if job_details:
                generated_image = create_job_post_image(job_details)
                if generated_image:
                    st.success("Image Generated Successfully!"); st.image(generated_image, caption="Preview (9:16 Story)", use_column_width=True)
                    st.markdown("---"); st.subheader("Download in Any Size")
                    for name, size in social_media_sizes.items():
                        resized_img = generated_image.resize(size, Image.Resampling.LANCZOS); buf = BytesIO(); resized_img.save(buf, format="PNG")
                        st.download_button(label=f"Download {name}", data=buf.getvalue(), file_name=f"job_post_{size[0]}x{size[1]}.png", mime="image/png")
    else: st.warning("Please enter a URL.")
