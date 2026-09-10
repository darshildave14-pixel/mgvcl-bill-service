import streamlit as st
import fitz  # PyMuPDF
import re
import os
import json
import requests

# --- Page Config ---
st.set_page_config(page_title="MGVCL Bill Finder", layout="centered")

st.title("⚡ MGVCL Consumer Bill Finder")
st.caption("Developed by: Darshil Dave | Contact: 7383302817 | Piplag Sub Division")

PDF_PATH = "bills.pdf"
INDEX_PATH = "bills_index.json"

# --- Sidebar: Monthly PDF Setup ---
with st.sidebar:
    st.header("⚙️ Monthly PDF Setup")
    download_url = st.text_input(
        "Direct PDF Link (Dropbox / Direct Link):", 
        placeholder="https://.../bills.pdf?dl=1"
    )
    
    if st.button("Download & Index Master PDF"):
        if download_url:
            # Auto-fix Dropbox links if entered with dl=0
            if "dropbox.com" in download_url and "dl=0" in download_url:
                download_url = download_url.replace("dl=0", "dl=1")

            status_placeholder = st.empty()
            progress_bar = st.progress(0)

            status_placeholder.info("⏳ Downloading large PDF... Please wait.")

            try:
                # Stream the download to avoid memory spikes
                with requests.get(download_url, stream=True, timeout=300) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0

                    with open(PDF_PATH, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress_bar.progress(min(downloaded / total_size, 1.0))

                status_placeholder.info("📑 File downloaded. Indexing all Consumer Numbers...")
                progress_bar.progress(0)

                doc = fitz.open(PDF_PATH)
                total_pages = len(doc)
                consumer_index = {}
                pattern = re.compile(r'(?:ગ્રાહક\s*નંબર|Consumer\s*No\.?)[:\s]*(\d{10,12})')

                for i in range(total_pages):
                    text = doc[i].get_text()
                    match = pattern.search(text)
                    if match:
                        consumer_index[match.group(1).strip()] = i
                    else:
                        fallback = re.findall(r'\b\d{11}\b', text)
                        for num in fallback:
                            consumer_index[num] = i

                    if i % 150 == 0 or i == total_pages - 1:
                        progress_bar.progress((i + 1) / total_pages)

                doc.close()

                # Save index cache
                with open(INDEX_PATH, "w", encoding="utf-8") as f:
                    json.dump(consumer_index, f)

                status_placeholder.success(f"✅ Indexed {len(consumer_index)} bills across {total_pages} pages!")
                st.rerun()

            except Exception as e:
                status_placeholder.error(f"❌ Download failed: {str(e)}")
        else:
            st.warning("Please paste a valid download link.")

# --- Main App: Search & View ---
if not os.path.exists(PDF_PATH) or not os.path.exists(INDEX_PATH):
    st.info("👈 Open the sidebar and paste your Dropbox/Direct download link to initialize this month's bills.")
else:
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        consumer_index = json.load(f)

    consumer_no = st.text_input("Enter Consumer No (ગ્રાહક નંબર):", placeholder="e.g. 52501027280", max_chars=12)

    if st.button("🔍 Search Bill"):
        c_num = consumer_no.strip()
        if c_num in consumer_index:
            page_num = consumer_index[c_num]
            doc = fitz.open(PDF_PATH)
            
            # Extract single page as PDF
            single_doc = fitz.open()
            single_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            pdf_bytes = single_doc.tobytes()
            
            # Render high-resolution preview image
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            
            doc.close()
            single_doc.close()

            st.success(f"Consumer {c_num} found on Page {page_num + 1}!")
            
            # Direct Download / Print Button
            st.download_button(
                label="🖨️ Download / Print Single Bill (PDF)",
                data=pdf_bytes,
                file_name=f"MGVCL_Bill_{c_num}.pdf",
                mime="application/pdf"
            )

            # High-res bill preview
            st.image(img_bytes, caption=f"Bill: {c_num}", use_container_width=True)
        else:
            st.error(f"Consumer number '{c_num}' not found.")
