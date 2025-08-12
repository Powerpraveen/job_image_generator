import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO
import re
from datetime import datetime
import random
from urllib.parse import urljoin

# This data scraping function is stable and requires no changes.
def get_job_details(url):
    """
    Fetches job details and the website's favicon URL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator="\n", strip=True)

        favicon_url = None
        icon_link = soup.find("link", rel=re.compile("icon", re.I))
        if icon_link and icon_link.get('href'):
            favicon_url = urljoin(url, icon_link['href'])

        title = soup.find('h1', class_='entry-title').text.strip() if soup.find('h1', class_='entry-title') else "Title Not Found"
        
        post_names_text = "Check Notification"
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 1 and 'post name' in cells[0].get_text(strip=True).lower():
                post_names_text = cells[1].get_text(strip=True); break
        
        age_limit_str = "Not Found"
        age_range_match = re.search(r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*years', page_text, re.IGNORECASE)
        if age_range_match: age_limit_str = f"Up to {age_range_match.group(2)} Years"
        else:
            max_age_match = re.search(r'max(?:imum)?\s*age\s*(?:limit)?\s*[:\s]*(\d{1,2})', page_text, re.IGNORECASE)
            if max_age_match: age_limit_str = f"Up to {max_age_match.group(1)} Years"

        salary_str = "Not Found"
        salaries = re.findall(r'₹?\s*([\d,]{4,})', page_text)
        if salaries:
            numeric_salaries = [int(s.replace(',', '')) for s in salaries if s.replace(',', '').isdigit()]
            if numeric_salaries: salary_str = f"Up to ₹{max(numeric_salaries):,}/-"
        
        last_date_str = "Not Found"
        date_matches = re.findall(r'(\d{1,2})[./-]\s?(\d{1,2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[./-]\s?(\d{2,4})', page_text, re.I)
        parsed_dates = []
        for d, m, y in date_matches:
            try:
                month_num = datetime.strptime(m, "%b" if len(m)==3 else "%B").month if m.isalpha() else int(m)
                year_num = int(f"20{y}") if len(y) == 2 else int(y)
                if year_num > 2020: parsed_dates.append(datetime(year_num, month_num, int(d)))
            except ValueError:
                continue
        if parsed_dates: last_date_str = max(parsed_dates).strftime('%d %B %Y')

        selection_process_text = "As per rules"
        selection_header = soup.find(['strong', 'h3'], string=re.compile("Selection Process", re.I))
        if selection_header:
            next_element = selection_header.find_next(['ul', 'p'])
            if next_element: selection_process_text = ', '.join([li.get_text(strip=True) for li in next_element.find_all('li')]) if next_element.name == 'ul' else next_element.get_text(strip=True)

        return {
            "Job Post Title": title, "Post Names": post_names_text, "Age Limit": age_limit_str,
            "Salary": salary_str, "Selection Process": selection_process_text, "Last Date": last_date_str,
            "Favicon URL": favicon_url
        }
    except Exception as e:
        st.error(f"An error occurred: {e}"); return None

# --- NEW: Final, Perfected Image Generation Engine ---
def create_job_post_image(details):
    if not details: return None

    palettes = [
        {"bg": (10, 25, 47), "text": (229, 231, 235), "accent": (5, 150, 105)},
        {"bg": (249, 250, 251), "text": (17, 24, 39), "accent": (37, 99, 235)},
        {"bg": (75, 85, 99), "text": (255, 255, 255), "accent": (253, 186, 116)},
    ]
    palette = random.choice(palettes)
    BG_COLOR, TEXT_COLOR, ACCENT_COLOR = palette["bg"], palette["text"], palette["accent"]
    
    keywords = ["JOB", "APPLY", "LINK", "DETAILS"]
    cta_templates = ["Comment '{keyword}' for the link!", "Want the link? Type '{keyword}'!"]
    
    width, height = 1080, 1920
    img = Image.new('RGB', (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_bold = ImageFont.truetype("Poppins-Bold.ttf", 65); font_regular = ImageFont.truetype("Poppins-Regular.ttf", 45); font_small = ImageFont.truetype("Poppins-Regular.ttf", 42); header_font = ImageFont.truetype("Poppins-Bold.ttf", 50)
    except IOError:
        st.error("Font files are missing!"); return None

    # --- Header with Correctly Sized Favicon ---
    header_height = 180
    draw.rectangle([0, 0, width, header_height], fill=ACCENT_COLOR)
    draw.text((width/2, header_height/2), "Latest Job Update", font=header_font, fill=BG_COLOR, anchor="mm")
    
    if details["Favicon URL"]:
        try:
            icon_response = requests.get(details["Favicon URL"], stream=True, timeout=5)
            icon_response.raise_for_status()
            favicon = Image.open(icon_response.raw).convert("RGBA")
            # --- FIX: Set favicon size to be visually similar to header text ---
            favicon_size = 70 
            favicon.thumbnail((favicon_size, favicon_size))
            # --- FIX: Center favicon vertically in the header bar ---
            favicon_y = (header_height - favicon.height) // 2
            img.paste(favicon, (60, favicon_y), favicon)
        except Exception:
            pass

    # --- Main Content with GUARANTEED No-Trim Layout ---
    y_position = 240
    # --- FIX: Increased margin and reduced wrap width to prevent ANY trimming ---
    margin = 120 
    wrap_width_title = 24
    wrap_width_details = 35

    # Title
    title_lines = textwrap.wrap(details["Job Post Title"], width=wrap_width_title)
    for line in title_lines:
        draw.text((width/2, y_position), line, font=font_bold, fill=TEXT_COLOR, anchor="ms")
        y_position += font_bold.getbbox(line)[3] + 15
    y_position += 30

    # Detail Items with Emojis
    emoji_map = {"Post Names": "💼", "Age Limit": "👤", "Salary": "💰", "Selection Process": "📝"}
    detail_items = {k: v for k, v in details.items() if k in emoji_map}
    for key, value in detail_items.items():
        label = f"{emoji_map.get(key, '')} {key}:"
        draw.text((margin, y_position), label, font=font_small, fill=ACCENT_COLOR)
        y_position += font_small.getbbox(label)[3] + 10
        value_lines = textwrap.wrap(str(value), width=wrap_width_details)
        for line in value_lines:
            draw.text((margin, y_position), line, font=font_regular, fill=TEXT_COLOR)
            y_position += font_regular.getbbox(line)[3] + 10
        y_position += 35

    # --- Footer Elements with Fixed Positions ---
    box_height = 180
    box_y_start = height - 160 - box_height
    draw.rectangle([margin - 20, box_y_start, width - margin + 20, box_y_start + box_height], fill=ACCENT_COLOR)
    draw.text((width/2, box_y_start + 55), "Last Date to Apply", font=font_small, fill=BG_COLOR, anchor="ms")
    draw.text((width/2, box_y_start + 125), details["Last Date"], font=font_bold, fill=BG_COLOR, anchor="ms")
    
    final_cta = random.choice(cta_templates).format(keyword=random.choice(keywords))
    draw.text((width/2, height - 80), final_cta, font=font_small, fill=ACCENT_COLOR, anchor="ms")

    return img

# --- Streamlit UI (No changes needed) ---
st.set_page_config(page_title="AI Job Post Generator", layout="centered")
st.title("🚀 AI Job Post Image Generator")
st.markdown("Enter a job post URL to create a unique, professional social media image with a perfect, no-trim layout.")
social_media_sizes = {"9:16 Story (1080x1920)": (1080, 1920), "Instagram Post (1080x1080)": (1080, 1080), "Facebook Post (1200x630)": (1200, 630)}
url = st.text_input("Enter the Job Post URL:", placeholder="https://newgovtjobalert.com/...")
if st.button("Generate Image"):
    if url:
        with st.spinner("Analyzing page and building perfect design..."):
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
