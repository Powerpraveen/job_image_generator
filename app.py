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
    Fetches and parses job details from a URL with truly intelligent pattern matching.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text(separator="\n", strip=True)

        # --- Intelligent Extraction Logic ---

        # 1. Job Post Title
        title_element = soup.find('h1', class_='entry-title')
        title = title_element.text.strip() if title_element else "Title Not Found"

        # 2. Post Names
        post_names_text = "Check Notification"
        for tag in soup.find_all(['strong', 'b']):
            if 'post name' in tag.get_text(strip=True).lower():
                # Find the next sibling or parent's next sibling to get the value
                if tag.find_next_sibling():
                    post_names_text = tag.find_next_sibling().get_text(strip=True)
                    break
                elif tag.parent.find_next_sibling():
                     post_names_text = tag.parent.find_next_sibling().get_text(strip=True)
                     break
        if post_names_text == "Check Notification":
             for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) > 1 and 'post name' in cells[0].get_text(strip=True).lower():
                    post_names_text = cells[1].get_text(strip=True)
                    break

        # --- NEW: Truly Intelligent Age Limit Search ---
        age_limit_str = "Not Found"
        # Pattern to find keywords like "Age Limit", "Age", etc.
        age_keyword_pattern = re.compile(r'(age\slimit|age)', re.IGNORECASE)
        # Search through all text on the page
        for element in soup.find_all(string=age_keyword_pattern):
            # Check the text of the element itself and its parent container
            search_text = element.parent.get_text(strip=True)
            
            # Pattern 1: "18 to 28 Years" or "18-28 Years"
            match = re.search(r'(\d{2})\s*(?:to|-)\s*(\d{2})\s*years', search_text, re.IGNORECASE)
            if match:
                age_limit_str = f"{match.group(1)} to {match.group(2)} Years"
                break
            
            # Pattern 2: "Minimum 21 Years"
            match = re.search(r'min(?:imum)?\s*age\s*[:\s]*(\d{2})', search_text, re.IGNORECASE)
            if match:
                age_limit_str = f"Minimum {match.group(1)} Years"
                break
            
            # Pattern 3: "Maximum 30 Years"
            match = re.search(r'max(?:imum)?\s*age\s*[:\s]*(\d{2})', search_text, re.IGNORECASE)
            if match:
                age_limit_str = f"Up to {match.group(1)} Years"
                break
        
        if age_limit_str == "Not Found":
            # Fallback for simple number ranges if keyword search fails
            match = re.search(r'(\d{2})-(\d{2})\s*Years', page_text)
            if match:
                age_limit_str = f"{match.group(1)} to {match.group(2)} Years"

        # 4. Salary (finds the highest value)
        salary_str = "Not Found"
        salaries = re.findall(r'₹?\s*([\d,]{4,})\s*(?:/-)?', page_text)
        numeric_salaries = [int(s.replace(',', '')) for s in salaries if s.replace(',', '').isdigit()]
        if numeric_salaries:
            salary_str = f"Up to ₹{max(numeric_salaries):,}/-"

        # 5. Last Date (finds the latest date)
        last_date_str = "Not Found"
        date_matches = re.findall(r'(\d{2})[./-](\d{2})[./-](\d{4})', page_text)
        parsed_dates = []
        for d, m, y in date_matches:
            try:
                parsed_dates.append(datetime(int(y), int(m), int(d)))
            except ValueError:
                continue
        if parsed_dates:
            latest_date = max(parsed_dates)
            last_date_str = latest_date.strftime('%d %B %Y')

        details = {
            "Job Post Title": title,
            "Post Names": post_names_text,
            "Age Limit": age_limit_str,
            "Salary": salary_str,
            "Last Date": last_date_str
        }
        return details

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch URL: {e}")
        return None

# --- (The create_job_post_image function and Streamlit UI remain the same) ---
def create_job_post_image(details):
    if not details:
        return None

    palettes = [
        {"bg": (245, 245, 245), "text": (40, 40, 40), "accent": (26, 140, 140)},
        {"bg": (230, 240, 255), "text": (50, 60, 80), "accent": (0, 102, 204)},
        {"bg": (255, 248, 240), "text": (60, 45, 45), "accent": (200, 80, 70)},
        {"bg": (34, 40, 49), "text": (238, 238, 238), "accent": (0, 173, 181)},
        {"bg": (253, 253, 253), "text": (20, 20, 20), "accent": (96, 108, 129)},
    ]
    palette = random.choice(palettes)
    BG_COLOR, TEXT_COLOR, ACCENT_COLOR = palette["bg"], palette["text"], palette["accent"]

    footer_texts = [
        "Share with friends who need this!", "Tag someone who should apply!", "Don't miss this opportunity!",
        "Your next career move is here.", "Apply now & spread the word!", "Is this the job for you? Apply now!",
        "Help someone find their dream job.", "Good luck with your application!", "Visit the website for more details.",
        "Check the official notification to apply."
    ]

    width, height = 1080, 1920
    img = Image.new('RGB', (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_bold = ImageFont.truetype("Poppins-Bold.ttf", size=80)
        font_regular = ImageFont.truetype("Poppins-Regular.ttf", size=50)
        font_small = ImageFont.truetype("Poppins-Regular.ttf", size=45)
    except IOError:
        st.error("Font files are missing! Ensure Poppins-Bold.ttf and Poppins-Regular.ttf are in your repository.")
        return None

    total_text_length = sum(len(str(v)) for v in details.values())
    header_text = "Job Update" if total_text_length > 200 else "Government Job Alert"
    header_font = ImageFont.truetype("Poppins-Bold.ttf", size=60 if header_text == "Job Update" else 50)
    
    draw.rectangle([0, 0, width, 200], fill=ACCENT_COLOR)
    draw.text((width/2, 100), header_text, font=header_font, fill=BG_COLOR, anchor="mm")

    y_position = 320
    wrapped_title = textwrap.wrap(details["Job Post Title"], width=22)
    for line in wrapped_title:
        draw.text((width/2, y_position), line, font=font_bold, fill=TEXT_COLOR, anchor="ms")
        y_position += 85

    y_position += 80
    detail_items = {k: v for k, v in details.items() if k not in ["Job Post Title", "Last Date"]}
    for key, value in detail_items.items():
        draw.text((100, y_position), f"{key}:", font=font_small, fill=ACCENT_COLOR)
        value_y = y_position + 60
        wrapped_value = textwrap.wrap(str(value), width=35)
        for line in wrapped_value:
            draw.text((100, value_y), line, font=font_regular, fill=TEXT_COLOR)
            value_y += 60
        y_position = value_y + 30

    draw.rectangle([50, y_position, width - 50, y_position + 200], fill=ACCENT_COLOR)
    draw.text((width/2, y_position + 70), "Last Date to Apply", font=font_small, fill=BG_COLOR, anchor="ms")
    draw.text((width/2, y_position + 140), details["Last Date"], font=font_bold, fill=BG_COLOR, anchor="ms")
    
    draw.text((width/2, height - 100), random.choice(footer_texts), font=font_small, fill=ACCENT_COLOR, anchor="ms")

    return img

st.set_page_config(page_title="Dynamic Job Post Generator", layout="centered")
st.title("🚀 Intelligent Job Post Image Generator")
st.markdown("Enter a job post URL. The tool will intelligently create a unique, professional social media image every time.")

social_media_sizes = {
    "9:16 Story (1080x1920)": (1080, 1920),
    "Instagram Post (1080x1080)": (1080, 1080),
    "Facebook Post (1200x630)": (1200, 630),
    "Twitter Post (1024x512)": (1024, 512)
}

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
                    
                    st.markdown("---")
                    st.subheader("Download in Any Size")
                    
                    for name, size in social_media_sizes.items():
                        resized_img = generated_image.resize(size, Image.Resampling.LANCZOS)
                        
                        buf = BytesIO()
                        resized_img.save(buf, format="PNG")
                        byte_im = buf.getvalue()

                        st.download_button(
                            label=f"Download {name}",
                            data=byte_im,
                            file_name=f"job_post_{size[0]}x{size[1]}.png",
                            mime="image/png"
                        )
    else:
        st.warning("Please enter a URL to generate an image.")
