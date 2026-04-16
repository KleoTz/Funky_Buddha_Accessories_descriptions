import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# 1. Ρυθμίσεις Σελίδας
st.set_page_config(page_title="Magento Accessories Porter", page_icon="🛍️")

st.title("🛍️ Magento Accessories Porter")
st.markdown("Επικολλήστε τα **STYLE NR.** για να δημιουργήσετε το CSV εισαγωγής.")

# 2. Σύνδεση μέσω gspread
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
    
    # Άνοιγμα του Spreadsheet
    spreadsheet_id = "1rP1cqvVWQsslZhJrfVxRDarHptFRCCCwkc06TPJdmDc"
    sh = gc.open_by_key(spreadsheet_id)
    worksheet = sh.worksheet("Sheet1") 
    
    # Λήψη όλων των δεδομένων
    all_data = worksheet.get_all_records()
    df_master = pd.DataFrame(all_data)
    
    # Καθαρισμός κεφαλίδων
    df_master.columns = [str(c).strip() for c in df_master.columns]
    
    if 'STYLE NR.' in df_master.columns:
        df_master['STYLE NR.'] = df_master['STYLE NR.'].astype(str).str.strip()
    else:
        st.error(f"❌ Η στήλη 'STYLE NR.' δεν βρέθηκε στο Sheet1. Βρέθηκαν: {list(df_master.columns)}")
        st.stop()

except Exception as e:
    st.error(f"❌ Σφάλμα σύνδεσης: {e}")
    st.stop()

# 3. UI - Περιοχή Επικόλλησης
input_data = st.text_area("Επικολλήστε τα STYLE NR. εδώ (ένα ανά γραμμή):", height=250)

if st.button("🚀 Δημιουργία CSV & Ενημέρωση Λίστας"):
    if input_data.strip():
        # Καθαρισμός εισαγωγής χρήστη
        input_list = list(set([s.strip() for s in input_data.split('\n') if s.strip()]))
        
        # Εύρεση αντιστοιχιών στη βάση
        matches = df_master[df_master['STYLE NR.'].isin(input_list)].copy()
        found_styles = matches['STYLE NR.'].unique()
        missing_styles = [s for s in input_list if s not in found_styles]

        if not matches.empty:
            # 4. Δημιουργία CSV & Έλεγχος για κενές περιγραφές
            csv_lines = ["sku,store_view_code,short_description"]
            empty_desc_styles = [] 
            
            for _, row in matches.iterrows():
                def clean_val(text):
                    # Επιστρέφει None αν είναι κενό/μηδέν/NaN
                    if pd.isna(text) or text == 0 or text == "0" or str(text).strip() == "":
                        return None
                    return str(text).replace('"', "'").replace('\n', ' ').replace('\r', ' ').strip()

                d_gr = clean_val(row.get('description_gr', ''))
                d_en = clean_val(row.get('description_en', ''))
                sku_c = str(row.get('sku_chroma', '')).strip()
                style_nr = str(row.get('STYLE NR.', '')).strip()

                # Έλεγχος για κενά
                if d_gr is None or d_en is None:
                    if style_nr not in empty_desc_styles:
                        empty_desc_styles.append(style_nr)

                # Διαχείριση None για το CSV
                d_gr_final = d_gr if d_gr else ""
                d_en_final = d_en if d_en else ""

                csv_lines.append(f'"{sku_c}","","{d_gr_final}"')
                csv_lines.append(f'"{sku_c}","el","{d_gr_final}"')
                csv_lines.append(f'"{sku_c}","en","{d_en_final}"')

            csv_string = "\ufeff" + "\n".join(csv_lines)
            
            # 5. Ενημέρωση Ημερομηνίας στο Google Sheet
            try:
                current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
                header = [h.strip() for h in worksheet.row_values(1)]
                
                if 'processed_date' in header:
                    col_date_idx = header.index('processed_date') + 1
                    col_style_idx = header.index('STYLE NR.') + 1
                    
                    # Παίρνουμε όλη τη στήλη των Style NR
                    styles_in_sheet = worksheet.col_values(col_style_idx)
                    
                    # Ενημέρωση κάθε γραμμής που ταιριάζει
                    for style in found_styles:
                        for row_idx, value in enumerate(styles_in_sheet, start=1):
                            if str(value).strip() == str(style).strip():
                                worksheet.update_cell(row_idx, col_date_idx, current_time)
                
                st.success(f"✅ Επεξεργάστηκαν {len(found_styles)} κωδικοί και ενημερώθηκε η λίστα!")
            except Exception as update_err:
                st.warning(f"⚠️ Το CSV δημιουργήθηκε, αλλά η ενημέρωση της λίστας απέτυχε: {update_err}")

            # 6. Εμφάνιση Logs & Download
            if empty_desc_styles:
                with st.warning("⚠️ Προσοχή: Βρέθηκαν κωδικοί με ελλιπή περιγραφή!"):
                    with st.expander("Δείτε τους κωδικούς (Λείπει GR ή EN)"):
                        for s in empty_desc_styles:
                            st.write(f"• {s}")

            st.download_button(
                label="📥 Λήψη CSV για Magento",
                data=csv_string,
                file_name=f"magento_import_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.error("❌ Δεν βρέθηκε κανένας από τους κωδικούς στη λίστα.")
            
        if missing_styles:
            with st.expander("❌ Κωδικοί που ΔΕΝ υπάρχουν στη λίστα"):
                for m in missing_styles:
                    st.write(f"• {m}")
    else:
        st.warning("Παρακαλώ επικολλήστε κάποια δεδομένα.")

st.divider()
st.caption("Funky Buddha Accessories Porter v2.1")
