import streamlit as st
import openpyxl
import requests
import os
import re
import time

# Load configuration from Streamlit Secrets
def load_config():
    config = st.secrets["openwebui"]
    return {
        "endpoint": config["endpoint"],
        "api_key": config["api_key"]
    }

config = load_config()
api_endpoint = config['endpoint']
api_key = config['api_key']

# Load translation prompt template
def load_prompt_template():
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        st.error("prompt.txt file missing! Create it with the translation template.")
        st.stop()

PROMPT_TEMPLATE = load_prompt_template()

# Language style mapping
def get_language_style_for_class(student_class):
    class_to_age_mapping = {
        'A': 'for a 3-year-old child',
        'B': 'for a 4-year-old child',
        'C': 'for a 5-year-old child',
        '1': 'for a 6-year-old child',
        '2': 'for a 7-year-old child',
        '3': 'for a 8-year-old child',
        '4': 'for a 9-year-old child',
        '5': 'for a 10-year-old child'
    }
    return class_to_age_mapping.get(student_class, 'for a 6-year old')

# Text processing utilities
def is_hindi_text(text):
    return len(re.findall(r'[\u0900-\u097F]', text)) >= 2

def split_text_parts(text):
    return re.split(r'(<br>|\[.*?\])', text)

# API request handler with error handling
def openwebui_request(cleaned_text, language_style, model="us.deepseek.r1-v1:0"):
    try:
        prompt = PROMPT_TEMPLATE.format(
            language_style=language_style,
            text=cleaned_text
        )
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
        headers = {"Authorization": f"Bearer {api_key}"}

        for attempt in range(3):
            try:
                response = requests.post(
                    api_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json().get("choices", [{}])[0].get("message", {}).get("content", cleaned_text)
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                st.warning(f"Attempt {attempt+1}/3 failed: {str(e)}")
                time.sleep(2)
                
        st.error("Translation failed after 3 attempts")
        return cleaned_text

    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return cleaned_text

# Excel processing logic
def process_excel(file):
    try:
        workbook = openpyxl.load_workbook(file)
        sheet = workbook.active

        class_column_index = None
        valid_classes = ['A','B','C','1','2','3','4','5']

        for col in sheet.iter_cols(1, sheet.max_column):
            if col[0].value == 'Class':
                class_column_index = col[0].col_idx - 1

        if class_column_index is None:
            st.error("'Class' column not found.")
            return None, []

        output_data = []
        error_count = 0

        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            try:
                student_class = str(row[class_column_index].value).strip()
                if student_class not in valid_classes:
                    st.warning(f"Row {row_idx}: Invalid class '{student_class}'")
                    error_count += 1
                    continue

                language_style = get_language_style_for_class(student_class)

                for cell in row:
                    if isinstance(cell.value, str):
                        parts = split_text_parts(cell.value)
                        translated_parts = []
                        
                        for part in parts:
                            if is_hindi_text(part):
                                cleaned = part.strip()
                                translated = openwebui_request(cleaned, language_style)
                                translated_parts.append(translated)
                            else:
                                translated_parts.append(part)
                                
                        cell.value = ''.join(translated_parts)
                        output_data.append({
                            "Original": cell.value,
                            "Translated": cell.value
                        })

                if error_count > 5:
                    st.error("Too many errors - stopping processing")
                    break

            except Exception as e:
                st.error(f"Error processing row {row_idx}: {str(e)}")
                continue

        return workbook, output_data

    except Exception as e:
        st.error(f"Excel processing error: {str(e)}")
        return None, []

# Streamlit UI
def main():
    st.title('Hindi-English Translator')
    
    with st.expander("ℹ️ Instructions"):
        st.markdown("""
        - Upload Excel file with 'Class' column
        - Supported classes: A, B, C, 1-5
        - Hindi text automatically translated
        """)

    uploaded_file = st.file_uploader("Choose Excel file", type="xlsx")

    if uploaded_file:
        workbook, output_data = process_excel(uploaded_file)
        
        if workbook:
            st.success("Translation complete!")
            output_filename = f"{os.path.splitext(uploaded_file.name)[0]}_en.xlsx"
            
            with st.spinner("Saving file..."):
                workbook.save(output_filename)
                with open(output_filename, "rb") as f:
                    st.download_button(
                        "📥 Download Translated File",
                        f,
                        file_name=output_filename
                    )

if __name__ == '__main__':
    main()