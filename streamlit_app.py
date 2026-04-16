import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. Ρυθμίσεις Σελίδας
st.set_page_config(page_title="Magento Accessories Porter", page_icon="🛍️")

st.title("🛍️ Magento Accessories Porter")
st.markdown("Επικολλήστε τα **STYLE NR.** για να δημιουργήσετε το CSV εισαγωγής.")

# 2. Σύνδεση μέσω gspread (Πιο σταθερή μέθοδος)
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    # Αντλούμε τα credentials από τα Streamlit Secrets
    creds_dict = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
    }
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
    
    # Άνοιγμα του Spreadsheet (χρησιμοποιούμε το ID από το URL σου)
    spreadsheet_id = "1rP1cqvVWQsslZhJrfVxRDarHptFRCCCwkc06TPJdmDc"
    sh = gc.open_by_key(spreadsheet_id)
    worksheet = sh.worksheet("Sheet1") # <--- ΒΕΒΑΙΩΣΟΥ ΟΤΙ ΤΟ TAB ΛΕΓΕΤΑΙ Sheet1
    
    # Λήψη όλων των δεδομένων
    all_data = worksheet.get_all_records()
    df_master = pd.DataFrame(all_data)
    
    # Καθαρισμός κενών στις κεφαλίδες και στα STYLE NR.
    df_master.columns = [str(c).strip() for c in df_master.columns]
    if 'STYLE NR.' in df_master.columns:
        df_master['STYLE NR.'] = df_master['STYLE NR.'].astype(str).str.strip()
    else:
        st.error(f"❌ Η στήλη 'STYLE NR.' δεν βρέθηκε. Βρέθηκαν: {list(df_master.columns)}")
        st.stop()

except Exception as e:
    st.error(f"❌ Σφάλμα σύνδεσης: {e}")
    st.info("Ελέγξτε αν το tab στο Google Sheets ονομάζεται ακριβώς 'Sheet1' και αν το Service Account έχει δικαιώματα Editor.")
    st.stop()

# 3. Περιοχή Επικόλλησης
input_data = st.text_area("Επικολλήστε τα STYLE NR. εδώ (ένα ανά γραμμή):", height=250)

if st.button("🚀 Δημιουργία CSV & Ενημέρωση Λίστας"):
    if input_data.strip():
        # Καθαρισμός εισαγωγής
        input_list = list(set([s.strip() for s in input_data.split('\n') if s.strip()]))
        
        # Εύρεση αντιστοιχιών
        matches = df_master[df_master['STYLE NR.'].isin(input_list)].copy()
        found_styles = matches['STYLE NR.'].unique()
        missing_styles = [s for s in input_list if s not in found_styles]

        if not matches.empty:
            # 4. Δημιουργία CSV Logic
            csv_lines = ["sku,store_view_code,short_description"]
            
            for _, row in matches.iterrows():
                def clean_val(text):
                    if pd.isna(text) or text == 0 or text == "0": return ""
                    return str(text).replace('"', "'").replace('\n', ' ').replace('\r', ' ').strip()

                d_gr = clean_val(row.get('description_gr', ''))
                d_en = clean_val(row.get('description_en', ''))
                sku_c = str(row.get('sku_chroma', '')).strip()

                csv_lines.append(f'"{sku_c}","","{d_gr}"')
                csv_lines.append(f'"{sku_c}","el","{d_gr}"')
                csv_lines.append(f'"{sku_c}","en","{d_en}"')

            csv_string = "\ufeff" + "\n".join(csv_lines)
            
            # 5. Ενημέρωση Ημερομηνίας στο Google Sheet
            try:
                current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # Βρίσκουμε τους αριθμούς γραμμών στο Sheet (gspread index ξεκινά από 2 λόγω header)
                # Θα κάνουμε update μόνο τη στήλη processed_date
                header = worksheet.row_values(1)
                if 'processed_date' in header:
                    col_idx = header.index('processed_date') + 1
                    
                    # Update για κάθε style που βρέθηκε
                    for style in found_styles:
                        # Βρίσκουμε όλες τις γραμμές που έχουν αυτό το Style NR.
                        cell_list = worksheet.findall(style, in_column=header.index('STYLE NR.')+1)
                        for cell in cell_list:
                            worksheet.update_cell(cell.row, col_idx, current_time)
                
                st.success(f"✅ Επεξεργάστηκαν {len(found_styles)} κωδικοί και ενημερώθηκε η λίστα!")
            except Exception as update_err:
                st.warning(f"Το CSV δημιουργήθηκε, αλλά η λίστα δεν ενημερώθηκε: {update_err}")

            # 6. Download Button
            st.download_button(
                label="📥 Λήψη CSV για Magento",
                data=csv_string,
                file_name=f"magento_import_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.error("Δεν βρέθηκε κανένας από τους κωδικούς στη λίστα.")
            
        if missing_styles:
            with st.expander("Δείτε τους κωδικούς που λείπουν"):
                for m in missing_styles:
                    st.write(f"❌ {m}")
    else:
        st.warning("Παρακαλώ επικολλήστε δεδομένα.")

st.divider()
st.caption("Funky Buddha Accessories Tool v2.0 (Stable)")
