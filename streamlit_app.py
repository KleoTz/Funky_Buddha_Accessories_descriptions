import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Ρυθμίσεις Σελίδας
st.set_page_config(page_title="Magento CSV Generator_Accessories", page_icon="🛍️")

st.title("🛍️ Magento Accessories Porter")
st.markdown("Επικολλήστε τα **STYLE NR.** για να δημιουργήσετε το CSV εισαγωγής.")

# 1. Σύνδεση με τη σταθερή λίστα στο Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Διαβάζουμε τη MAIN λίστα (Google Sheet)
    # Η λίστα πρέπει να έχει στήλες: sku_chroma, STYLE NR., description_gr, description_en, processed_date
    df_master = conn.read(ttl="0") 
    df_master['STYLE NR.'] = df_master['STYLE NR.'].astype(str).str.strip()
except Exception as e:
    st.error(f"Σφάλμα σύνδεσης με τη λίστα: {e}")
    st.stop()

# 2. Περιοχή Επικόλλησης
input_data = st.text_area("Επικολλήστε τα STYLE NR. εδώ (ένα ανά γραμμή):", height=250)

if st.button("Δημιουργία CSV & Ενημέρωση Λίστας"):
    if input_data.strip():
        # Καθαρισμός των Style Numbers από το input
        input_list = list(set([s.strip() for s in input_data.split('\n') if s.strip()]))
        
        # Αναζήτηση στη Main Λίστα
        matches = df_master[df_master['STYLE NR.'].isin(input_list)].copy()
        found_styles = matches['STYLE NR.'].unique()
        missing_styles = [s for s in input_list if s not in found_styles]

        if not matches.empty:
            # 3. Δημιουργία περιεχομένου CSV για Magento
            # Format: sku, store_view_code, short_description
            csv_lines = ["sku,store_view_code,short_description"]
            
            for _, row in matches.iterrows():
                def clean(text):
                    if pd.isna(text) or text == 0 or text == "0": return ""
                    return str(text).replace('"', "'").replace('\n', ' ').replace('\r', ' ').strip()

                d_gr = clean(row['description_gr'])
                d_en = clean(row['description_en'])
                sku_c = str(row['sku_chroma']).strip()

                # Magento Logic: 3 εγγραφές ανά κωδικό χρώματος
                csv_lines.append(f'"{sku_c}","","{d_gr}"')   # All Store Views (Default)
                csv_lines.append(f'"{sku_c}","el","{d_gr}"') # Greek View
                csv_lines.append(f'"{sku_c}","en","{d_en}"') # English View

            # CSV με BOM για σωστά ελληνικά στο Excel
            csv_string = "\ufeff" + "\n".join(csv_lines)
            
            # 4. Ενημέρωση ημερομηνίας στη Main Λίστα
            #current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
            #df_master.loc[df_master['STYLE NR.'].isin(found_styles), 'processed_date'] = current_time
            #conn.update(data=df_master)

            current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
            # Ενημερώνουμε τη στήλη processed_date για τα STYLE NR που βρέθηκαν
            df_master.loc[df_master['STYLE NR.'].isin(found_styles), 'processed_date'] = current_time

            # Ενημέρωση του Google Sheet
            # Προσθέτουμε το spreadsheet URL και το worksheet όνομα ρητά για να μη χαθεί η σύνδεση
            conn.update(
                spreadsheet="https://docs.google.com/spreadsheets/d/1rP1cqvVWQsslZhJrfVxRDarHptFRCCCwkc06TPJdmDc/edit?usp=sharing",
                worksheet="Sheet1",
                data=df_master
            )
            st.success(f"Επεξεργάστηκαν {len(found_styles)} κωδικοί!")

            # 5. Download Button
            st.download_button(
                label="📥 Λήψη CSV για Magento",
                data=csv_string,
                file_name=f"magento_import_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.error("Δεν βρέθηκε κανένας από τους κωδικούς στη λίστα.")
            
        if missing_styles:
            with st.expander("Δείτε τους κωδικούς που λείπουν (Missing)"):
                for m in missing_styles:
                    st.write(f"❌ {m}")
    else:
        st.warning("Παρακαλώ επικολλήστε κάποια δεδομένα.")

st.divider()
st.caption("Funky Buddha Accessories Tool - Shared via GitHub & Streamlit")
