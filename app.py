import streamlit as st
import openpyxl
from openai import OpenAI
import os
import re

# Load API key securely from Streamlit secrets
def load_api_key():
    return st.secrets["openai"]["api_key"]

# Load prompt template from file
def load_prompt_template():
    with open("prompt.txt", "r") as file:
        return file.read()

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

# Clean the Hindi text before translation
def clean_text(text):
    return text.strip()

# Split a cell into translatable and non-translatable parts
def split_text_parts(text):
    return re.split(r'(<br>|\[.*?\])', text)

# Perform translation using OpenAI API
def translate_text_via_openai(text, api_key, prompt_template, language_style):
    client = OpenAI(api_key=api_key)
    prompt = prompt_template.replace("{{text}}", text).replace("{{language_style}}", language_style)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful translator."},
            {"role": "user", "content": prompt}
        ]
    )
    translated_text = response.choices[0].message.content.strip()
    tokens_used = response.usage.total_tokens  # Track usage
    return translated_text, tokens_used

# Process the Excel file
def process_excel(file, api_key, prompt_template):
    workbook = openpyxl.load_workbook(file)
    sheet = workbook.active

    class_column_index = None
    total_tokens_used = 0

    for col in sheet.iter_cols(1, sheet.max_column):
        if col[0].value == 'Class':
            class_column_index = col[0].col_idx - 1  # Zero-indexed

    if class_column_index is None:
        st.error("Column 'Class' not found in the Excel sheet.")
        return None

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
                        translated, tokens_used = translate_text_via_openai(cleaned, api_key, prompt_template, language_style)
                        translated_parts.append(translated)
                        total_tokens_used += tokens_used
                    else:
                        translated_parts.append(part)

                cell.value = ''.join(translated_parts)

    st.write(f"Total tokens used for your file: {total_tokens_used}")
    return workbook

# Streamlit app UI
def main():
    st.title('Hindi to English Question Translator')

    uploaded_file = st.file_uploader("Upload Excel File (ensure that the excel has a 'Class' column)", type="xlsx")

    if uploaded_file:
        api_key = load_api_key()
        prompt_template = load_prompt_template()
        workbook = process_excel(uploaded_file, api_key, prompt_template)

        if workbook:
            input_filename = os.path.splitext(uploaded_file.name)[0]
            output_filename = f"{input_filename}_en.xlsx"

            with open(output_filename, 'wb') as f:
                workbook.save(f)

            with open(output_filename, 'rb') as f:
                st.success('Translation completed!')
                st.download_button('Download Translated File', f, file_name=output_filename)

if __name__ == '__main__':
    main()
