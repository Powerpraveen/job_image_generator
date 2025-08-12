import streamlit as st
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import re, textwrap, random
from datetime import datetime
from urllib.parse import urljoin

# -------------------- Utilities for pixel-accurate text --------------------
def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def wrap_text_px(text, font, max_width_px):
    words = (text or "").split()
    if not words:
        return [""]
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= max_width_px or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def text_block_height(lines, font, line_spacing_px):
    total = 0
    for line in lines:
        bbox = font.getbbox(line or " ")
        total += (bbox[3] - bbox[1]) + line_spacing_px
    return total

# -------------------- Scraper with robust matching --------------------
def get_job_details(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        page_text = soup.get_text(separator="\n", strip=True)

        # Favicon
        favicon_url = None
        icon_link = soup.find("link", rel=re.compile(r"icon", re.I))
        if icon_link and icon_link.get("href"):
            favicon_url = urljoin(url, icon_link["href"])

        # Title
        title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "Title Not Found"

        # Post Names: table -> strong/bold -> regex fallback
        post_name = "Check Notification"
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) > 1 and "post name" in tds[0].get_text(strip=True).lower():
                post_name = tds[1].get_text(strip=True)
                break
        if post_name == "Check Notification":
            for tag in soup.find_all(["strong", "b"]):
                t = tag.get_text(" ", strip=True).lower()
                if "post name" in t or re.search(r"\bpost\b", t):
                    sibling_text = (tag.find_next_sibling(text=True) or "").strip()
                    if len(sibling_text) > 2:
                        post_name = sibling_text
                        break
        if post_name == "Check Notification":
            m = re.search(r"(?:post\s*name|name\s*of\s*post)\s*[:\-]\s*(.+)", page_text, re.I)
            if m:
                post_name = m.group(1).split("\n")[0].strip()

        # Age limit (prefer max)
        age_limit = "Not Found"
        m = re.search(r'(\d{1,2})\s*(?:to|-|–)\s*(\d{1,2})\s*years', page_text, re.I)
        if m:
            age_limit = f"Up to {m.group(2)} Years"
        else:
            m = re.search(r'max(?:imum)?\s*age\s*(?:limit)?\s*[:\-]?\s*(\d{1,2})', page_text, re.I)
            if m:
                age_limit = f"Up to {m.group(1)} Years"

        # Salary: pick highest large numeric; raw strings and no illegal escapes
        salary = "Not Found"
        salary_matches = re.findall(
            r'(?:₹|Rs\.?|rs\.?)?\s*([\d,]{4,})\s*(?:/-)?',
            page_text,
            flags=re.IGNORECASE
        )
        nums = []
        for s in salary_matches:
            clean = s.replace(',', '')
            if clean.isdigit():
                v = int(clean)
                if v >= 3000:
                    nums.append(v)
        if nums:
            salary = f"Up to ₹{max(nums):,}/-"

        # Selection process
        selection = "As per rules"
        sel_header = soup.find(['strong', 'h3', 'h4'], string=re.compile(r"Selection Process", re.I))
        if sel_header:
            nxt = sel_header.find_next(['ul', 'ol', 'p', 'div'])
            if nxt:
                if nxt.name in ('ul', 'ol'):
                    items = [li.get_text(" ", strip=True) for li in nxt.find_all('li')]
                    if items:
                        selection = ", ".join(items)
                else:
                    txt = nxt.get_text(" ", strip=True)
                    if len(txt) > 3:
                        selection = txt

        # Last Date: handle “22 August 2025”, “22 Aug 2025”, “22-08-2025”, “2/8/25”
        last_date = "Not Found"
        parsed = []

        # 1) D Month YYYY
        for d, mon, y in re.findall(r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{2,4})', page_text):
            try:
                mon_num = datetime.strptime(mon[:3], "%b").month
                yr = int(y) if len(y) == 4 else int(f"20{y}")
                if yr >= 2021:
                    parsed.append(datetime(yr, mon_num, int(d)))
            except Exception:
                pass

        # 2) D/M/Y or D-M-Y or D.M.Y
        for d, mth, y in re.findall(r'(\d{1,2})[./\-]\s*(\d{1,2})[./\-]\s*(\d{2,4})', page_text):
            try:
                yr = int(y) if len(y) == 4 else int(f"20{y}")
                if yr >= 2021:
                    parsed.append(datetime(yr, int(mth), int(d)))
            except Exception:
                pass

        # 3) Prefer lines with last/closing date keywords
        lines = page_text.split("\n")
        key = re.compile(r'(Last\s*Date|Closing\s*Date|Apply\s*Before)', re.I)
        for i, line in enumerate(lines):
            if key.search(line):
                window = " ".join(lines[i:i+3])
                for d, mon, y in re.findall(r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{2,4})', window):
                    try:
                        mon_num = datetime.strptime(mon[:3], "%b").month
                        yr = int(y) if len(y) == 4 else int(f"20{y}")
                        if yr >= 2021:
                            parsed.append(datetime(yr, mon_num, int(d)))
                    except Exception:
                        pass
                for d, mth, y in re.findall(r'(\d{1,2})[./\-]\s*(\d{1,2})[./\-]\s*(\d{2,4})', window):
                    try:
                        yr = int(y) if len(y) == 4 else int(f"20{y}")
                        if yr >= 2021:
                            parsed.append(datetime(yr, int(mth), int(d)))
                    except Exception:
                        pass

        if parsed:
            last_date = max(parsed).strftime('%d %B %Y')

        return {
            "Job Post Title": title,
            "Post Names": post_name,
            "Age Limit": age_limit,
            "Salary": salary,
            "Selection Process": selection,
            "Last Date": last_date,
            "Favicon URL": favicon_url
        }

    except Exception as e:
        st.error(f"Scraping error: {e}")
        return None

# -------------------- Poster renderer (no-overlap engine) --------------------
def create_job_post_image(details):
    if not details:
        return None

    # Professional palettes
    palettes = [
        {"bg": (10, 25, 47), "text": (229, 231, 235), "accent": (5, 150, 105)},   # Navy + Emerald
        {"bg": (249, 250, 251), "text": (17, 24, 39), "accent": (37, 99, 235)},   # Light + Blue
        {"bg": (33, 37, 41), "text": (248, 249, 250), "accent": (255, 193, 7)},   # Charcoal + Amber
        {"bg": (255, 255, 255), "text": (28, 28, 30), "accent": (124, 58, 237)},  # White + Purple
    ]
    pal = random.choice(palettes)
    BG, TXT, ACC = pal["bg"], pal["text"], pal["accent"]

    # Canvas and layout constants
    W, H = 1080, 1920
    margin = 120
    safe_w = W - 2 * margin
    header_h = 168
    date_box_h = 178
    footer_h = 90
    reserved_bottom = 30 + date_box_h + 24 + footer_h  # padding + box + padding + footer

    # Fonts initial
    title_px = 64
    label_px = 44
    body_px = 46
    header_px = 50
    footer_px = 40

    ft_title = load_font("Poppins-Bold.ttf", title_px)
    ft_label = load_font("Poppins-Bold.ttf", label_px)
    ft_body = load_font("Poppins-Regular.ttf", body_px)
    ft_header = load_font("Poppins-Bold.ttf", header_px)
    ft_footer = load_font("Poppins-Regular.ttf", footer_px)

    # Spacing
    gap_small = 8
    gap_body = 10
    gap_block = 22

    # Content
    title = details.get("Job Post Title", "Job Update")
    fields = [
        ("Post Names", "💼", details.get("Post Names", "")),
        ("Age Limit", "👤", details.get("Age Limit", "")),
        ("Salary", "💰", details.get("Salary", "")),
        ("Selection Process", "📝", details.get("Selection Process", "")),
    ]
    last_date_val = details.get("Last Date", "")

    # CTA
    keys = ["JOB", "LINK", "APPLY", "DETAILS", "INFO", "POST"]
    ctas = [
        "Comment '{k}' to get the link",
        "Type '{k}' below for the apply link",
        "Want details? Comment '{k}'",
        "Get the post link: type '{k}'",
    ]
    footer_text = random.choice(ctas).format(k=random.choice(keys))

    # Function to measure total height
    def total_height():
        t_lines = wrap_text_px(title, ft_title, safe_w)
        t_h = text_block_height(t_lines, ft_title, gap_small) + 6

        d_h = 0
        for label, emoji, value in fields:
            if not value:
                continue
            lbl = f"{emoji} {label}:"
            b = ft_label.getbbox(lbl)
            d_h += (b[3] - b[1]) + gap_small
            v_lines = wrap_text_px(str(value), ft_body, safe_w)
            d_h += text_block_height(v_lines, ft_body, gap_body)
            d_h += gap_block

        return header_h + 18 + t_h + 16 + d_h + reserved_bottom

    # Auto-shrink fonts if content too tall (prevents overlap)
    for _ in range(12):
        if total_height() <= H - 4:
            break
        if header_h > 136:
            header_h = int(header_h * 0.95)
        title_px = max(48, int(title_px * 0.94))
        label_px = max(34, int(label_px * 0.94))
        body_px = max(34, int(body_px * 0.94))
        header_px = max(42, int(header_px * 0.94))
        footer_px = max(34, int(footer_px * 0.94))
        ft_title = load_font("Poppins-Bold.ttf", title_px)
        ft_label = load_font("Poppins-Bold.ttf", label_px)
        ft_body = load_font("Poppins-Regular.ttf", body_px)
        ft_header = load_font("Poppins-Bold.ttf", header_px)
        ft_footer = load_font("Poppins-Regular.ttf", footer_px)

    # Draw
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, W, header_h], fill=ACC)
    draw.text((W//2, header_h//2), "Latest Job Update", font=ft_header, fill=BG, anchor="mm")

    # Favicon sized to header text height
    fav_url = details.get("Favicon URL")
    if fav_url:
        try:
            rr = requests.get(fav_url, timeout=5, stream=True)
            rr.raise_for_status()
            fav = Image.open(rr.raw).convert("RGBA")
            hb = ft_header.getbbox("Ag")
            target_h = max(40, min(header_h - 36, hb[3] - hb[1] + 8))
            scale = target_h / fav.height
            fav = fav.resize((int(fav.width * scale), target_h), Image.LANCZOS)
            fav_y = (header_h - fav.height) // 2
            img.paste(fav, (40, fav_y), fav)
        except Exception:
            pass

    y = header_h + 18

    # Title
    t_lines = wrap_text_px(title, ft_title, safe_w)
    for line in t_lines:
        draw.text((W//2, y), line, font=ft_title, fill=TXT, anchor="ma")
        bb = ft_title.getbbox(line)
        y += (bb[3] - bb[1]) + gap_small
    y += 12

    # Details
    for label, emoji, value in fields:
        if not value:
            continue
        lbl = f"{emoji} {label}:"
        draw.text((margin, y), lbl, font=ft_label, fill=ACC)
        lb = ft_label.getbbox(lbl)
        y += (lb[3] - lb[1]) + gap_small

        v_lines = wrap_text_px(str(value), ft_body, safe_w)
        for ln in v_lines:
            draw.text((margin, y), ln, font=ft_body, fill=TXT)
            vb = ft_body.getbbox(ln)
            y += (vb[3] - vb[1]) + gap_body
        y += gap_block

    # Last Date box (fixed above footer)
    box_y = H - reserved_bottom + 30
    draw.rounded_rectangle([margin-18, box_y, W-margin+18, box_y + date_box_h], radius=20, fill=ACC)
    draw.text((W//2, box_y + 56), "Last Date to Apply", font=ft_label, fill=BG, anchor="mm")
    draw.text((W//2, box_y + 118), last_date_val or "—", font=ft_title, fill=BG, anchor="mm")

    # Footer CTA (fixed)
    draw.text((W//2, H - 44), footer_text, font=ft_footer, fill=ACC, anchor="mm")

    return img

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="AI Job Post Image Generator", page_icon="🧰", layout="centered")
st.title("🚀 AI Job Post Image Generator")

st.markdown("Paste a job post URL. The app extracts Title, Post Name, Max Age Limit, Highest Salary, Selection Process, and the latest Last Date, then builds a poster with branding, emojis, and multiple download sizes.")

url = st.text_input("Job post URL")
sizes = {
    "9:16 Story (1080x1920)": (1080, 1920),
    "Instagram Square (1080x1080)": (1080, 1080),
    "Facebook Link (1200x630)": (1200, 630),
}

if st.button("Generate"):
    if not url:
        st.warning("Please paste a job post URL.")
    else:
        with st.spinner("Fetching and generating..."):
            data = get_job_details(url)
            if data:
                poster = create_job_post_image(data)
                if poster:
                    st.image(poster, caption="Preview (9:16)", use_column_width=True)
                    st.subheader("Download")
                    for name, wh in sizes.items():
                        buf = BytesIO()
                        poster.resize(wh, Image.LANCZOS).save(buf, format="PNG")
                        st.download_button(
                            label=f"Download {name}",
                            data=buf.getvalue(),
                            file_name=f"job_post_{wh[0]}x{wh[1]}.png",
                            mime="image/png"
                        )
