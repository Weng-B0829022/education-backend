import openai
import os
from dotenv import load_dotenv
from django.conf import settings

CHUNK_SIZE = 4000  # OpenAI API 的 token 限制約為 4096
SUMMARY_PROMPT = 'Summarise the following content in traditional Chinese:\n\n'
INTEGRATE_PROMPT = 'Integrate the following summaries into a comprehensive conclusion:\n\n'
load_dotenv(os.path.join(settings.BASE_DIR, '.env'))

def summerize_pdf_content(pdf_text: str) -> str:
    try:
        load_dotenv()
        client = openai.OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY'),
        )

        # 將長文本分割成較小的塊
        text_chunks = []
        for i in range(0, len(pdf_text), CHUNK_SIZE):
            text_chunks.append(pdf_text[i:i + CHUNK_SIZE])

        # 如果文本很短，直接總結
        if len(text_chunks) == 1:
            response = client.chat.completions.create(
                messages=[
                    {
                        'role': 'user',
                        'content': SUMMARY_PROMPT + text_chunks[0],
                    }
                ],
                model='gpt-3.5-turbo',
            )
            return response.choices[0].message.content

        # 對每個塊進行總結
        summaries = []
        for chunk in text_chunks:
            response = client.chat.completions.create(
                messages=[
                    {
                        'role': 'user',
                        'content': SUMMARY_PROMPT + chunk,
                    }
                ],
                model='gpt-3.5-turbo',
            )
            summaries.append(response.choices[0].message.content)

        # 整合所有總結
        final_response = client.chat.completions.create(
            messages=[
                {
                    'role': 'user',
                    'content': INTEGRATE_PROMPT + '\n'.join(summaries),
                }
            ],
            model='gpt-3.5-turbo',
        )

        return final_response.choices[0].message.content

    except Exception as e:
        print(f"Error processing PDF content: {str(e)}")
        return "Error processing PDF content" 