import streamlit as st
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import textwrap, re, random
from datetime import datetime
from urllib.parse import urljoin

# --- Scraper ---
def get_job_details(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        html = requests.get(url, headers=headers, timeout=10)
        html.raise_for_status()
        soup = BeautifulSoup(html.text, 'html.parser')
        text = soup.get_text(separator="\n", strip=True)

        # Favicon
        favicon_url = None
        icon_link = soup.find("link", rel=re.compile("icon", re.I))
        if icon_link and icon_link.get("href"):
            favicon_url = urljoin(url, icon_link["href"])

        # Title
        title = soup.find("h1", class_="entry-title")
        title_text = title.text.strip() if title else "Title Not Found"

        # Post Names
        post_names = "Check Notification"
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) > 1 and "post name" in cells[0].get_text(strip=True).lower():
                post_names = cells[1].get_text(strip=True)
                break

        # Age Limit - show max
        age_limit = "Not Found"
        m = re.search(r'(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\s*years', text, re.I)
        if m:
            age_limit = f"Up to {m.group(2)} Years"
        else:
            m = re.search(r'max(?:imum)?\s*age\s*(?:limit)?\s*[:\s]*(\d{1,2})', text, re.I)
            if m:
                age_limit = f"Up to {m.group(1)} Years"

        # Salary - pick highest
        salary = "Not Found"
        salaries = re.findall(r'₹?\s*([\d,]{4,})', text)
        nums = [int(s.replace(',', '')) for s in salaries if s.replace(',', '').isdigit()]
        if nums:
            salary = f"Up to ₹{max(nums):,}/-"

        # Last Date - flexible parsing, pick latest
        last_date = "Not Found"
        date_matches = re.findall(r'(\d{1,2})[./ -]\s?(\d{1,2}|[A-Za-z]{3,9})[a-z]*[./ -]\s?(\d{2,4})', text)
        parsed_dates = []
        for d, mth, y in date_matches:
            try:
                if mth.isalpha():
                    mth_num = datetime.strptime(mth[:3], "%b").month
                else:
                    mth_num = int(mth)
                year_num = int(f"20{y}") if len(y) == 2 else int(y)
                if year_num > 2020:
                    parsed_dates.append(datetime(year_num, mth_num, int(d)))
            except:
                pass
        if parsed_dates:
            last_date = max(parsed_dates).strftime('%d %B %Y')

        # Selection Process
        selection = "As per rules"
        sel_header = soup.find(['strong', 'h3'], string=re.compile("Selection Process", re.I))
        if sel_header:
            nxt = sel_header.find_next(['ul', 'p'])
            if nxt:
                selection = ', '.join([li.get_text(strip=True) for li in nxt.find_all('li')]) if nxt.name == "ul" else nxt.get_text(strip=True)

        return {
            "Job Post Title": title_text,
            "Post Names": post_names,
            "Age Limit": age_limit,
            "Salary": salary,
            "Selection Process": selection,
            "Last Date": last_date,
            "Favicon URL": favicon_url
        }
    except Exception as e:
        st.error(f"Scraping error: {e}")
        return None

# --- Text Wrap Helper ---
def wrap_text_px(text, font, max_width):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def text_height(lines, font, spacing):
    return sum((font.getbbox(line or " ")[3] - font.getbbox(line or " ")[1]) + spacing for line in lines)

# --- Renderer ---
def create_job_post_image(details):
    if not details: return None

    # Colors
    palettes = [
        {"bg": (10, 25, 47), "text": (229, 231, 235), "accent": (5, 150, 105)},
        {"bg": (249, 250, 251), "text": (17, 24, 39), "accent": (37, 99, 235)},
        {"bg": (33, 37, 41), "text": (248, 249, 250), "accent": (255, 193, 7)},
    ]
    BG_COLOR, TEXT_COLOR, ACCENT_COLOR = random.choice(palettes).values()

    # Canvas
    width, height = 1080, 1920
    margin, safe_width = 120, width - 240
    reserved_bottom = 90 + 30 + 180 + 30  # footer + padding + datebox + padding

    # Fonts
    def load_font(name, size):
        try: return ImageFont.truetype(name, size)
        except: return ImageFont.load_default()

    title_size, label_size, body_size, header_size = 64, 44, 46, 50
    font_title = load_font("Poppins-Bold.ttf", title_size)
    font_label = load_font("Poppins-Bold.ttf", label_size)
    font_body = load_font("Poppins-Regular.ttf", body_size)
    font_header = load_font("Poppins-Bold.ttf", header_size)
    font_footer = load_font("Poppins-Regular.ttf", 40)

    # Header & favicon
    img = Image.new("RGB", (width, height), BG_COLOR)
    d = ImageDraw.Draw(img)
    header_h = 170
    d.rectangle([0, 0, width, header_h], fill=ACCENT_COLOR)
    d.text((width//2, header_h//2), "Latest Job Update", font=font_header, fill=BG_COLOR, anchor="mm")

    if details["Favicon URL"]:
        try:
            r = requests.get(details["Favicon URL"], timeout=5, stream=True)
            r.raise_for_status()
            fav = Image.open(r.raw).convert("RGBA")
            target_h = font_header.getbbox("Ag")[3] + 8
            scale = target_h / fav.height
            fav = fav.resize((int(fav.width * scale), target_h), Image.LANCZOS)
            fav_y = (header_h - fav.height) // 2
            img.paste(fav, (40, fav_y), fav)
        except: pass

    # Draw content dynamically
    y = header_h + 20
    title_lines = wrap_text_px(details["Job Post Title"], font_title, safe_width)
    for line in title_lines:
        d.text((width//2, y), line, font=font_title, fill=TEXT_COLOR, anchor="ma")
        y += font_title.getbbox(line)[3] - font_title.getbbox(line)[1] + 8
    y += 18

    emoji_map = {"Post Names": "💼", "Age Limit": "👤", "Salary": "💰", "Selection Process": "📝"}
    for k in ["Post Names", "Age Limit", "Salary", "Selection Process"]:
        val = details[k]
        label_line = f"{emoji_map[k]} {k}:"
        d.text((margin, y), label_line, font=font_label, fill=ACCENT_COLOR)
        y += font_label.getbbox(label_line)[3] - font_label.getbbox(label_line)[1] + 5
        for line in wrap_text_px(val, font_body, safe_width):
            d.text((margin, y), line, font=font_body, fill=TEXT_COLOR)
            y += font_body.getbbox(line)[3] - font_body.getbbox(line)[1] + 5
        y += 20

    # Last Date box (fixed above footer)
    box_y = height - reserved_bottom + 30
    d.rounded_rectangle([margin-20, box_y, width-margin+20, box_y+180], radius=20, fill=ACCENT_COLOR)
    d.text((width//2, box_y+55), "Last Date to Apply", font=font_label, fill=BG_COLOR, anchor="mm")
    d.text((width//2, box_y+118), details["Last Date"], font=font_title, fill=BG_COLOR, anchor="mm")

    # Footer CTA
    keywords = ["JOB", "APPLY", "LINK", "DETAILS", "INFO"]
    ctas = ["Comment '{k}' for the link", "Type '{k}' below to get the link", "Want details? Comment '{k}'"]
    footer_text = random.choice(ctas).format(k=random.choice(keywords))
    d.text((width//2, height-45), footer_text, font=font_footer, fill=ACCENT_COLOR, anchor="mm")
    return img

# --- Streamlit UI ---
st.set_page_config(page_title="AI Job Post Generator", layout="centered")
st.title("🚀 AI Job Post Image Generator")
url = st.text_input("Enter Job Post URL:", "")
sizes = {
    "9:16 Story (1080x1920)": (1080, 1920),
    "Instagram (1080x1080)": (1080, 1080),
    "Facebook (1200x630)": (1200, 630)
}
if st.button("Generate Image"):
    if url:
        with st.spinner("Fetching & generating..."):
            details = get_job_details(url)
            if details:
                img = create_job_post_image(details)
                st.image(img, use_column_width=True)
                for name, size in sizes.items():
                    buf = BytesIO()
                    img.resize(size, Image.LANCZOS).save(buf, format="PNG")
                    st.download_button(f"Download {name}", buf.getvalue(), file_name=f"job_post_{size[0]}x{size[1]}.png", mime="image/png")
    else:
        st.warning("Please enter a URL.")
