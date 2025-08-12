import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO
import re
from datetime import datetime

def get_job_details(url):
    """
    Fetches and parses job details from a URL with intelligent pattern matching.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        # --- Intelligent Extraction Logic ---

        # 1. Job Post Title
        title_element = soup.find('h1', class_='entry-title')
        title = title_element.text.strip() if title_element else "Title Not Found"

        # 2. Post Names (finds all possibilities)
        post_names = set()
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 1 and 'post name' in cells[0].get_text(strip=True).lower():
                post_names.add(cells[1].get_text(strip=True))
        # Fallback search in text
        if not post_names:
            matches = re.findall(r"Name of Post\s*:\s*(.+)", page_text, re.IGNORECASE)
            for match in matches:
                post_names.add(match.strip())
        
        # 3. Age Limit (flexible parsing)
        age_limit_str = "Not Found"
        age_matches = re.search(r'(\d{1,2})\s*to\s*(\d{1,2})\s*years', page_text, re.IGNORECASE)
        if age_matches:
            age_limit_str = f"{age_matches.group(1)} to {age_matches.group(2)} Years"
        else:
            max_age_match = re.search(r'max(?:imum)?\s*age\s*limit\s*[:\s]*(\d{1,2})', page_text, re.IGNORECASE)
            if max_age_match:
                age_limit_str = f"Up to {max_age_match.group(1)} Years"

        # 4. Salary (finds the highest value)
        salary_str = "Not Found"
        # Matches numbers like 25,500 or 81100
        salaries = re.findall(r'₹?\s*([\d,]+)\s*(?:/-)?', page_text)
        numeric_salaries = [int(s.replace(',', '')) for s in salaries if s.replace(',', '').isdigit() and int(s.replace(',', '')) > 1000]
        if numeric_salaries:
            salary_str = f"Up to ₹{max(numeric_salaries):,}/-"

        # 5. Last Date (finds the latest date)
        last_date_str = "Not Found"
        # Matches DD-MM-YYYY, DD/MM/YYYY
        date_matches = re.findall(r'(\d{2})[/-](\d{2})[/-](\d{4})', page_text)
        parsed_dates = []
        for d, m, y in date_matches:
            try:
                parsed_dates.append(datetime(int(y), int(m), int(d)))
            except ValueError:
                continue # Ignore invalid dates like 99/99/9999
        if parsed_dates:
            latest_date = max(parsed_dates)
            last_date_str = latest_date.strftime('%d %B %Y')

        details = {
            "Job Post Title": title,
            "Post Names": ', '.join(post_names) if post_names else "Check Notification",
            "Age Limit": age_limit_str,
            "Salary": salary_str,
            "Last Date": last_date_str
        }
        return details

    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch URL: {e}")
        return None

def create_job_post_image(details):
    # This function remains the same as before, no changes needed here.
    if not details:
        return None

    BG_COLOR = (22, 28, 45)
    TEXT_COLOR = (255, 255, 255)
    ACCENT_COLOR = (0, 217, 255)
    
    width, height = 1080, 1920
    img = Image.new('RGB', (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_bold = ImageFont.truetype("Poppins-Bold.ttf", size=85)
        font_regular = ImageFont.truetype("Poppins-Regular.ttf", size=50)
        font_label = ImageFont.truetype("Poppins-Regular.ttf", size=45)
    except IOError:
        st.error("Font files not found! Please ensure 'Poppins-Bold.ttf' and 'Poppins-Regular.ttf' are in the repository.")
        return None

    draw.rectangle([0, 0, width, 250], fill=ACCENT_COLOR)
    draw.text((width/2, 125), "GOVERNMENT JOB ALERT", font=font_regular, fill=BG_COLOR, anchor="mm")
    
    wrapped_title = textwrap.wrap(details["Job Post Title"], width=20)
    y_position = 350
    for line in wrapped_title:
        draw.text((width/2, y_position), line, font=font_bold, fill=TEXT_COLOR, anchor="ms")
        y_position += 90

    y_position += 80
    detail_items = {k: v for k, v in details.items() if k not in ["Job Post Title", "Last Date"]}

    for key, value in detail_items.items():
        draw.text((100, y_position), f"{key}:", font=font_label, fill=ACCENT_COLOR)
        
        # Wrap detail text if it's too long
        wrapped_value = textwrap.wrap(value, width=30)
        value_y = y_position + 60
        for line in wrapped_value:
            draw.text((100, value_y), line, font=font_regular, fill=TEXT_COLOR)
            value_y += 60

        y_position += 120 + (len(wrapped_value) * 60) # Adjust spacing based on wrapped lines

    draw.rectangle([50, y_position, width - 50, y_position + 200], fill=ACCENT_COLOR)
    draw.text((width/2, y_position + 70), "Last Date to Apply", font=font_label, fill=BG_COLOR, anchor="ms")
    draw.text((width/2, y_position + 140), details["Last Date"], font=font_bold, fill=BG_COLOR, anchor="ms")
    
    draw.text((width/2, height - 100), "newgovtjobalert.com", font=font_label, fill=ACCENT_COLOR, anchor="ms")

    return img

# --- Streamlit App Interface (No changes needed from here down) ---
st.set_page_config(page_title="Job Post Image Generator", layout="centered")
st.title("🚀 Intelligent Job Post Image Generator")

st.markdown("Enter a URL from a job posting site. The tool will intelligently find the details and create a professional social media image.")

social_media_sizes = {
    "9:16 Story (1080x1920)": (1080, 1920),
    "Instagram Post (1080x1080)": (1080, 1080),
    "Facebook Post (1200x630)": (1200, 630),
    "Twitter Post (1024x512)": (1024, 512)
}

url = st.text_input("Enter the Job Post URL:", placeholder="https://newgovtjobalert.com/...")

if st.button("Generate Image"):
    if url:
        with st.spinner("Analyzing page and creating image..."):
            job_details = get_job_details(url)
            if job_details:
                generated_image = create_job_post_image(job_details)
                
                if generated_image:
                    st.success("Image Generated Successfully!")
                    st.image(generated_image, caption="Preview (9:16 Story)", use_column_width=True)
                    
                    st.markdown("---")
                    st.subheader("Download Your Image")
                    
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
