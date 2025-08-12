import streamlit as st
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import BytesIO

def get_job_details(url):
    """
    Fetches and parses job details from a given URL.
    """
    try:
        # Use a header to mimic a browser visit
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_element = soup.find('h1', class_='entry-title')
        title = title_element.text.strip() if title_element else "Title Not Found"

        details = {
            "Job Post Title": title,
            "Post Names": "Not Found",
            "Age Limit": "Not Found",
            "Salary": "Not Found",
            "Last Date": "Not Found"
        }

        # Scan for details within table rows or list items
        for row in soup.find_all(['tr', 'li']):
            cells = row.find_all('td')
            if len(cells) > 1:
                key = cells[0].get_text().lower()
                value = cells[1].text.strip()
                if "post name" in key:
                    details["Post Names"] = value
                elif "age limit" in key:
                    details["Age Limit"] = value
                elif "pay scale" in key or "salary" in key:
                    details["Salary"] = value
                elif "last date" in key:
                    details["Last Date"] = value
        
        return details
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch URL: {e}")
        return None

def create_job_post_image(details):
    """
    Creates a visually appealing image with the job details.
    """
    if not details:
        return None

    BG_COLOR = (22, 28, 45)
    TEXT_COLOR = (255, 255, 255)
    ACCENT_COLOR = (0, 217, 255)
    
    # Base image is 9:16
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

    # Header
    draw.rectangle([0, 0, width, 250], fill=ACCENT_COLOR)
    draw.text((width/2, 125), "GOVERNMENT JOB ALERT", font=font_regular, fill=BG_COLOR, anchor="mm")
    
    # Wrapped Job Title
    wrapped_title = textwrap.wrap(details["Job Post Title"], width=20)
    y_position = 350
    for line in wrapped_title:
        draw.text((width/2, y_position), line, font=font_bold, fill=TEXT_COLOR, anchor="ms")
        y_position += 90

    # Details Section
    y_position += 80
    detail_items = {k: v for k, v in details.items() if k not in ["Job Post Title", "Last Date"]}

    for key, value in detail_items.items():
        draw.text((100, y_position), f"{key}:", font=font_label, fill=ACCENT_COLOR)
        draw.text((100, y_position + 60), value, font=font_regular, fill=TEXT_COLOR)
        y_position += 180

    # Last Date Section
    draw.rectangle([50, y_position, width - 50, y_position + 200], fill=ACCENT_COLOR)
    draw.text((width/2, y_position + 70), "Last Date to Apply", font=font_label, fill=BG_COLOR, anchor="ms")
    draw.text((width/2, y_position + 140), details["Last Date"], font=font_bold, fill=BG_COLOR, anchor="ms")
    
    # Footer
    draw.text((width/2, height - 100), "newgovtjobalert.com", font=font_label, fill=ACCENT_COLOR, anchor="ms")

    return img

# --- Streamlit App Interface ---
st.set_page_config(page_title="Job Post Image Generator", layout="centered")
st.title("🚀 Automatic Job Post Image Generator")

st.markdown("Enter a URL from a job posting site, and this tool will automatically create a professional social media image for you.")

# Define social media sizes
social_media_sizes = {
    "9:16 Story (1080x1920)": (1080, 1920),
    "Instagram Post (1080x1080)": (1080, 1080),
    "Facebook Post (1200x630)": (1200, 630),
    "Twitter Post (1024x512)": (1024, 512)
}

# Input URL from user
url = st.text_input("Enter the Job Post URL:", placeholder="https://newgovtjobalert.com/...")

if st.button("Generate Image"):
    if url:
        with st.spinner("Fetching details and creating image..."):
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
