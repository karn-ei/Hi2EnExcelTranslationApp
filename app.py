import streamlit as st
import openpyxl
import toml
from openai import OpenAI

# Load API key from TOML file
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
        '3': 'for a 8-year old child',
        '4': 'for a 9-year old child',
        '5': 'for a 10-year-old child'
    }
    return class_to_age_language_mapping.get(student_class, 'for general audiences')

# Function to perform translation using OpenAI API
def translate_text_via_openai(text, api_key, prompt_template, language_style):
    client = OpenAI(api_key=api_key)
    prompt = prompt_template.replace("{{text}}", text).replace("{{language_style}}", language_style)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful translator."},
            {"role": "user", "content": prompt}
        ]
    )
    translated_text = response.choices[0].message.content.strip()
    return translated_text

# Function to handle Excel file
def process_excel(file, api_key, prompt_template):
    workbook = openpyxl.load_workbook(file)
    sheet = workbook.active

    class_column_index = None
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
                translated_text = translate_text_via_openai(cell.value, api_key, prompt_template, language_style)
                cell.value = translated_text

    return workbook

# Streamlit app interface
def main():
    st.title('Hindi to English Question Translator using OpenAI')

    uploaded_file = st.file_uploader("Upload Excel File", type="xlsx")

    if uploaded_file:
        api_key = load_api_key()
        prompt_template = load_prompt_template()
        workbook = process_excel(uploaded_file, api_key, prompt_template)

        if workbook:
            st.success('Translation completed!')
            with open('translated_questions.xlsx', 'wb') as f:
                workbook.save(f)

            with open('translated_questions.xlsx', 'rb') as f:
                st.download_button('Download Translated File', f, file_name='translated_questions.xlsx')

if __name__ == '__main__':
    main()
