import streamlit as st
import openpyxl
import requests
import os
import re

# Load configuration from Streamlit Secrets
def load_config():
    config = st.secrets["openwebui"]
    return {
        "endpoint": config["endpoint"],
        "api_key": config["api_key"]
    }

config = load_config()

# Extract endpoint and API key
api_endpoint = config['endpoint']
api_key = config['api_key']

# Determine language complexity based on class/age
def get_language_style_for_class(student_class):
    class_to_age_language_mapping = {
        'A': 'for a 3-year-old child',
        'B': 'for a 4-year-old child',
        'C': 'for a 5-year-old child',
        '1': 'for a 6-year-old child',
        '2': 'for a 7-year-old child',
        '3': 'for a 8-year-old child',
        '4': 'for a 9-year-old child',
        '5': 'for a 10-year-old child'
    }
    return class_to_age_language_mapping.get(student_class, 'for a 6-year old')

# Check if a part contains significant Hindi text
def is_hindi_text(text):
    return len(re.findall(r'[\u0900-\u097F]', text)) >= 3

# Split a cell into translatable and non-translatable parts
def split_text_parts(text):
    return re.split(r'(<br>|\[.*?\])', text)

# Clean the Hindi text before translation
def clean_text(text):
    return text.strip()

# Function to send request to OpenWebUI
def openwebui_request(text, model):
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": text}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.post(api_endpoint, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", text)
    return text

# Process the Excel file
def process_excel(file):
    workbook = openpyxl.load_workbook(file)
    sheet = workbook.active
    class_column_index = None

    # Identify the Class column
    for col in sheet.iter_cols(1, sheet.max_column):
        if col[0].value == 'Class':
            class_column_index = col[0].col_idx - 1

    # If Class column not found, show error
    if class_column_index is None:
        st.error("'Class' column not found in the Excel sheet.")
        return None, []

    output_data = []

    for row in sheet.iter_rows(min_row=2):  # Skip header
        student_class = row[class_column_index].value
        language_style = get_language_style_for_class(student_class)

        for cell in row:
            if isinstance(cell.value, str):
                parts = split_text_parts(cell.value)
                translated_parts = []

                for part in parts:
                    if is_hindi_text(part):
                        cleaned = clean_text(part)
                        # Translate using DeepSeek
                        translated = openwebui_request(cleaned, "deepseek-chat")
                        translated_parts.append(translated)
                    else:
                        translated_parts.append(part)

                # Combine translated parts and store in output_data
                original_text = cell.value
                translated_text = ''.join(translated_parts)
                output_data.append({"Original Text": original_text, "Translated Text": translated_text})

                # Update cell value with the translated text
                cell.value = translated_text

    return workbook, output_data

# Streamlit app
def main():
    st.title('OpenWebUI Hindi to English Translator')

    uploaded_file = st.file_uploader("Upload Excel File", type="xlsx")

    if uploaded_file:
        # Process the Excel file and get the output data
        workbook, output_data = process_excel(uploaded_file)

        # Display the data in Streamlit
        if output_data:
            st.write("Translation Results:")
            st.write(output_data)

        # Generate output filename
        output_filename = os.path.splitext(uploaded_file.name)[0] + "_en.xlsx"

        # Save the workbook
        with open(output_filename, 'wb') as f:
            workbook.save(f)

        # Provide download link
        with open(output_filename, 'rb') as f:
            st.download_button('Download Translated File', f, file_name=output_filename)

if __name__ == '__main__':
    main()
