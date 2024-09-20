import requests
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import docx2txt
import whisper
from youtube_transcript_api import YouTubeTranscriptApi
import vimeo_dl
import io
import os
from urllib.parse import urlparse
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain_community.docstore.document import Document
import tiktoken
from openai import OpenAI
from typing import List, Dict
import openai
from pinecone import Pinecone, ServerlessSpec
from models.assistant import Content
from collections import defaultdict
import json
pc = Pinecone(
    api_key=os.getenv('PINECONE_API_KEY')
)

if 'bamanai' not in pc.list_indexes().names():
    pc.create_index(
        name='bamanai', 
        dimension=1536, 
        metric='cosine',
        spec=ServerlessSpec(
            cloud='aws',
            region='us-east-1'
        )
    )
index = pc.Index('bamanai')

class Utils:
    @staticmethod
    def get_file_type(url):
        parsed_url = urlparse(url)
        path = parsed_url.path
        file_extension = os.path.splitext(path)[1].lower()

        if file_extension in ['.pdf', '.docx', '.txt']:
            return file_extension[1:]
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            return 'image'
        elif file_extension in ['.mp3', '.wav', '.ogg']:
            return 'audio'
        elif file_extension in ['.mp4', '.avi', '.mov']:
            return 'video'
        elif 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
            return 'youtube'
        elif 'vimeo.com' in parsed_url.netloc:
            return 'vimeo'
        else:
            raise ValueError('Unsupported file type')

    @staticmethod
    def extract_text(file_url, file_type):
        try:
            response = requests.get(file_url)
            response.raise_for_status()
            content = response.content
            
            if file_type == 'pdf':
                return Utils.extract_text_from_pdf(content)
            elif file_type == 'docx':
                return Utils.extract_text_from_docx(content)
            elif file_type == 'txt':
                return content.decode('utf-8')
            elif file_type == 'image':
                return Utils.extract_text_from_image(content)
            elif file_type in ['audio', 'video']:
                return Utils.extract_text_from_audio_video(file_url)  # Changed to use URL
            elif file_type == 'youtube':
                return Utils.extract_text_from_youtube(file_url)
            elif file_type == 'vimeo':
                return Utils.extract_text_from_vimeo(file_url)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Error extracting text: {str(e)}")

    @staticmethod
    def extract_text_from_pdf(content):
        images = convert_from_bytes(content)
        text = ""
        for image in images:
            text += pytesseract.image_to_string(image)
        return text

    @staticmethod
    def extract_text_from_docx(content):
        docx_file = io.BytesIO(content)
        text = docx2txt.process(docx_file)
        return text

    @staticmethod
    def extract_text_from_image(content):
        image = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(image)

    @staticmethod
    def extract_text_from_audio_video(url):
        model = whisper.load_model("base")
        result = model.transcribe(url)
        return result["text"]

    @staticmethod
    def extract_text_from_youtube(url):
        video_id = url.split("v=")[1]
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])

    @staticmethod
    def extract_text_from_vimeo(url):
        v = vimeo_dl.new(url)
        subtitle_url = v.subtitles()[0].url
        response = requests.get(subtitle_url)
        return response.text

    @staticmethod
    def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
        encoding = tiktoken.get_encoding(encoding_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    @staticmethod
    def create_chunks(text: str, chunk_size: int = 1500, chunk_overlap: int = 50) -> List[str]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=lambda x: Utils.num_tokens_from_string(x),
        )
        return text_splitter.split_text(text)

    @staticmethod
    def get_summary(text: str, max_tokens: int) -> str:
        llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-1106")
        prompt_template = PromptTemplate(
            input_variables=["text", "max_tokens"],
            template="""
            Summarize the following text in up to {max_tokens} tokens:

            Text: {text}
            """
        )
        chain = LLMChain(llm=llm, prompt=prompt_template)
        summary = chain.run({"text": text, "max_tokens": max_tokens})
        return summary

    @staticmethod
    def get_metadata(text: str) -> Dict[str, List[str]]:
        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            Extract the following information from the given text:
            1. Title (single string)
            2. Topics (list of strings)
            3. Keywords (list of strings)
            4. Questions (that this content can answer) (list of strings)

            Provide the output in JSON format.

            Text: {text}
            """
        )
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts metadata from text."},
                {"role": "user", "content": prompt.format(text=text)}
            ],
            temperature=0
        )
        return Utils.extract_json_data(response.choices[0].message.content)

    @staticmethod
    def extract_json_data(response):
      """
      Extract JSON data from the response.
      
      :param response: Response from the API.
      :return: JSON data.
      """
      # trim the response from first occurence of '{' to the last occurence of '}'
      start = response.find('{')
      end = response.rfind('}') + 1
      response = response[start:end]
      response = json.loads(response)
      return response
    
    @staticmethod
    def get_embeddings(text: str) -> List[float]:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    @staticmethod
    def upload_to_pinecone(assistant_id: str, content_id: str, digest_id: str, label_type: str, text: str, o_or_s_label: str):
        embeddings = Utils.get_embeddings(text)
        print('###### UPLOADING TO PINECONE ######')
        pinecone_id = f"{assistant_id}__{content_id}__{digest_id}__{label_type}__{o_or_s_label}"
        metadata = {
            "assistant_id": assistant_id,
            "label_type": label_type,
            "o_or_s_label": o_or_s_label
        }
        index.upsert(vectors=[{
            "id": pinecone_id,
            "values": embeddings,
            "metadata": metadata
        }])

    @staticmethod
    def process_and_upload_embeddings(assistant_id: str, content_id: str, digest_id: str, content: Content, o_or_s_label: str):
        Utils.upload_to_pinecone(assistant_id, content_id, digest_id, "text", content.content, o_or_s_label)
        Utils.upload_to_pinecone(assistant_id, content_id, digest_id, "title", content.title, o_or_s_label)
        Utils.upload_to_pinecone(assistant_id, content_id, digest_id, "topics", ", ".join(content.topics), o_or_s_label)
        Utils.upload_to_pinecone(assistant_id, content_id, digest_id, "keywords", ", ".join(content.keywords), o_or_s_label)

    @staticmethod
    def extract_chat_metadata(text: str) -> Dict[str, str]:
        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            Extract the following information from the given text:
            1. RefinedQuestion (single string)
            2. Topics (list of strings)
            3. Title (single string)
            4. Keywords (list of strings)

            Provide the output in JSON format.

            Text: {text}
            """
        )
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts metadata from text."},
                {"role": "user", "content": prompt.format(text=text)}
            ],
            temperature=0
        )
        return Utils.extract_json_data(response.choices[0].message.content)

    @staticmethod
    def generate_chat_response(user_message: str, conversation_summary: str, last_two_messages: List[Dict[str, str]], own_context: List[Dict[str, str]], supported_context: List[Dict[str, str]]) -> str:
        context = {
            'own': own_context,
            'supported': supported_context
        }
        prompt = PromptTemplate(
            input_variables=["user_message", "conversation_summary", "last_two_messages", "context"],
            template="""
            Given the following conversation summary, the last two messages, and the context from relevant content, generate a response to the user's message. Adapt the response fully according to the language, persona, and tonality of the original texts in own_content.

            Conversation Summary: {conversation_summary}
            Last Two Messages: {last_two_messages}
            User Message: {user_message}
            Context: {context}

            Response:
            """
        )
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates responses based on conversation context."},
                {"role": "user", "content": prompt.format(user_message=user_message, conversation_summary=conversation_summary, last_two_messages=last_two_messages, context=context)}
            ],
            temperature=0
        )
        return response.choices[0].message.content

    @staticmethod
    def query_pinecone(assistant_id: str, embedding: List[float], o_or_s_label: str, metadata_label: str) -> List[Dict[str, float]]:
        query_response = index.query(
            vector=embedding,
            top_k=10,
            include_metadata=True,
            filter={
                "assistant_id": assistant_id,
                "o_or_s_label": o_or_s_label,
                "label_type": metadata_label
            }
        )
        return [{"id": match["id"], "score": match["score"]} for match in query_response["matches"]]

    @staticmethod
    def update_conversation_summary(previous_summary: str, user_message: str, assistant_response: str) -> str:
        prompt = PromptTemplate(
            input_variables=["previous_summary", "user_message", "assistant_response"],
            template="""
            Given the previous conversation summary, the user's message, and the assistant's response, update the conversation summary.

            Previous Summary: {previous_summary}
            User Message: {user_message}
            Assistant Response: {assistant_response}

            Updated Summary:
            """
        )
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that updates conversation summaries."},
                {"role": "user", "content": prompt.format(previous_summary=previous_summary, user_message=user_message, assistant_response=assistant_response)}
            ],
            temperature=0
        )
        return response.choices[0].message.content

    @staticmethod
    def rank_pinecone_matches(matches: Dict[str, List[Dict[str, float]]]) -> List[Dict[str, float]]:
        weights = {
            'title': 3,
            'content': 2,
            'topics': 1,
            'keywords': 1
        }

        combined_scores = defaultdict(float)

        for label, label_matches in matches.items():
            weight = weights.get(label, 1)
            for match in label_matches:
                match_id = match['id']
                match_score = match['score']
                # Extract content_id and digest_id from the match_id
                match_parts = match_id.split('__')
                content_id = match_parts[1]
                digest_id = match_parts[2]
                unique_id = f"{content_id}__{digest_id}"
                # Calculate weighted score
                weighted_score = weight * match_score
                combined_scores[unique_id] += weighted_score

        # Sort the unique combinations by their weighted scores in decreasing order
        sorted_matches = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)

        # Convert to the desired output format
        ranked_matches = [{'content_id_digest_id': k, 'weighted_score': v} for k, v in sorted_matches]

        return ranked_matches
    
    @staticmethod
    def send_wa_message(sender_id: str, phone_number: str, message: str, sender_access_token: str, type: str = "text", media_url: str = None, caption: str = None):
        url = f"https://graph.facebook.com/v20.0/{sender_id}/messages"
        headers = {
            "Authorization": f"Bearer {sender_access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": type,
            f"{type}": {"body": message, "preview_url": False} if type == "text" else {"link": media_url, "caption": caption or "Hello"}
        }
        print(data)
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(response.json())
        return response.json()