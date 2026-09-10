import streamlit as st
import fitz  # PyMuPDF
import re
import os
import json
import gdown  # pip install gdown

# --- Page Config ---
st.set_page_config(page_title="MGVCL Bill Finder", layout="centered")

st.title("⚡ MGVCL Consumer Bill Finder")
st.caption("Developed by: Darshil Dave | Contact: 7383302817 | Piplag Sub Division")

PDF_PATH = "bills.pdf"
INDEX_PATH = "bills_index.json"

# --- Sidebar: Easy Admin Update ---
with st.sidebar:
    st.header("⚙️ Monthly PDF Setup")
    drive_url = st.text_input("Google Drive Share Link:")
    if st.button("Download & Index New Month"):
        if drive_url:
            with st.spinner("Downloading PDF from Google Drive..."):
                if os.path.exists(PDF_PATH):
                    os.remove(PDF_PATH)
                if os.path.exists(INDEX_PATH):
                    os.remove(INDEX_PATH)
                
                # Download directly from Drive link
                gdown.download(url=drive_url, output=PDF_PATH, quiet=False, fuzzy=True)

            with st.spinner("Indexing consumer numbers across all pages..."):
                doc = fitz.open(PDF_PATH)
                consumer_index = {}
                pattern = re.compile(r'(?:ગ્રાહક\s*નંબર|Consumer\s*No\.?)[:\s]*(\d{10,12})')

                for i in range(len(doc)):
                    text = doc[i].get_text()
                    match = pattern.search(text)
                    if match:
                        consumer_index[match.group(1).strip()] = i
                    else:
                        fallback = re.findall(r'\b\d{11}\b', text)
                        for num in fallback:
                            consumer_index[num] = i
                doc.close()

                with open(INDEX_PATH, "w", encoding="utf-8") as f:
                    json.dump(consumer_index, f)

                st.success(f"Indexed {len(consumer_index)} bills successfully!")
                st.rerun()
        else:
            st.warning("Please paste a valid Google Drive link.")

# --- Main App: Search & View ---
if not os.path.exists(PDF_PATH) or not os.path.exists(INDEX_PATH):
    st.info("👈 Please paste your Google Drive PDF link in the sidebar to load the bills.")
else:
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        consumer_index = json.load(f)

    consumer_no = st.text_input("Enter Consumer No (ગ્રાહક નંબર):", placeholder="e.g. 52501027280", max_chars=12)

    if st.button("🔍 Search Bill"):
        c_num = consumer_no.strip()
        if c_num in consumer_index:
            page_num = consumer_index[c_num]
            doc = fitz.open(PDF_PATH)
            
            # Extract single page PDF
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

            # Bill preview image on phone screen
            st.image(img_bytes, caption=f"Bill: {c_num}", use_column_width=True)
        else:
            st.error(f"Consumer number '{c_num}' not found.")