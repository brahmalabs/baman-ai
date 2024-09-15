from mongoengine import connect
from flask import Flask, jsonify, request, g
import jwt
import datetime
from models.teacher import Teacher
from middlewares.authentication import token_required_teacher, token_required_student
from dotenv import load_dotenv
load_dotenv()
from flask_cors import CORS
from services.google_login import GoogleLogin 
import os
from models.assistant import Assistant, Content, DigestedContent
from models.student import Student
from models.conversation import Conversation, UserMessage, AssistantMessage, References
from utils import Utils


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

# Enable CORS for requests from http://localhost:3000
CORS(app)

connect(host=os.getenv('MONGO_URI'))

# Sample route for testing
@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Baman AI API!"})



@app.route('/verify-teacher', methods=['POST'])
def verify_teacher():
    google_token = request.headers.get('Authorization')
    if google_token is None:
        return jsonify({'error': 'Authorization header missing'}), 401

    # Remove 'Bearer ' prefix if present
    if google_token.startswith('Bearer '):
        google_token = google_token[7:]

    user_info = GoogleLogin.verify_google_token(google_token)
    if not user_info:
        return jsonify({'error': 'Invalid Google token'}), 401

    user = Teacher.objects(google_id=user_info['sub']).first()
    if not user:
        user = Teacher(
            google_id=user_info['sub'],
            email=user_info['email'],
            name=user_info.get('name', ''),
            profile_picture=user_info.get('picture', ''),
            created_at=datetime.datetime.now(datetime.UTC),
            last_login=datetime.datetime.now(datetime.UTC)
        )
        user.save()
    else:
        user.update(last_login=datetime.datetime.now(datetime.UTC))

    jwt_token = jwt.encode({
        'sub': user.google_id,
        'email': user.email,
        'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'jwt_token': jwt_token})

# Test Protected route that requires a valid JWT token
@app.route('/protected_teacher', methods=['GET'])
@token_required_teacher
def protected_teacher():
    return jsonify({'message': 'This is a protected route'})

# Route to create an assistant
@app.route('/create_assistant', methods=['POST'])
@token_required_teacher
def create_assistant():
    data = request.json
    subject = data.get('subject')
    class_name = data.get('class_name')

    if not subject or not class_name:
        return jsonify({'error': 'Subject and class name are required'}), 400

    assistant = Assistant(
        teacher=g.current_user,
        subject=subject,
        class_name=class_name
    )
    assistant.save()

    return jsonify({'message': 'Assistant created successfully', 'assistant_id': assistant.id})

# Route to get all assistants for a teacher
@app.route('/get_assistants', methods=['GET'])
@token_required_teacher
def get_assistants():
    assistants = Assistant.objects(teacher=g.current_user)
    assistants_list = [{'id': assistant.id, 'subject': assistant.subject, 'class_name': assistant.class_name} for assistant in assistants]

    return jsonify({'assistants': assistants_list})

# Endpoint to digest content
@app.route('/digest', methods=['POST'])
@token_required_teacher
def digest():
    data = request.json
    fileUrl = data.get('fileUrl')
    assistant_id = data.get('assistant_id')

    if not fileUrl:
        return jsonify({'error': 'File URL is required'}), 400

    file_type = Utils.get_file_type(fileUrl)

    try:
        text_content = Utils.extract_text(fileUrl, file_type)
        assistant = Assistant.objects(id=assistant_id).first()

        short_summary = Utils.get_summary(text_content, 100)
        long_summary = Utils.get_summary(text_content, 500)

        metadata = Utils.get_metadata(long_summary)

        content = Content(
            type=file_type,
            content=text_content,
            fileUrl=fileUrl,
            title=metadata['Title'],
            topics=metadata['Topics'],
            keywords=metadata['Keywords'],
            short_summary=short_summary,
            long_summary=long_summary
        )

        chunks = Utils.create_chunks(text_content)
        for chunk in chunks:
            chunk_metadata = Utils.get_metadata(chunk)
            digested_content = DigestedContent(
                content=chunk,
                title=chunk_metadata['Title'],
                topics=chunk_metadata['Topics'],
                keywords=chunk_metadata['Keywords'],
                short_summary=Utils.get_summary(chunk, 100),
                long_summary=Utils.get_summary(chunk, 500),
                questions=chunk_metadata['Questions']
            )
            content.digests.append(digested_content)

        content_type = data.get('content_type')
        if content_type == 'own':
            assistant.own_content.append(content)
            o_or_s_label = 'own'
        else:
            assistant.supporting_content.append(content)
            o_or_s_label = 'supported'

        assistant.save()

        # Process and upload embeddings
        content_id = content.id
        for digest in content.digests:
            digest_id = digest.id
            Utils.process_and_upload_embeddings(assistant_id, content_id, digest_id, digest, o_or_s_label)

        return jsonify({
            'message': f'Processed {file_type} file',
            'content': content.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Route for student verification
@app.route('/verify-student', methods=['POST'])
def verify_student():
    google_token = request.headers.get('Authorization')
    if google_token is None:
        return jsonify({'error': 'Authorization header missing'}), 401

    # Remove 'Bearer ' prefix if present
    if google_token.startswith('Bearer '):
        google_token = google_token[7:]

    user_info = GoogleLogin.verify_google_token(google_token)
    if not user_info:
        return jsonify({'error': 'Invalid Google token'}), 401

    user = Student.objects(google_id=user_info['sub']).first()
    if not user:
        user = Student(
            google_id=user_info['sub'],
            email=user_info['email'],
            name=user_info.get('name', ''),
            profile_picture=user_info.get('picture', ''),
            created_at=datetime.datetime.now(datetime.UTC),
            last_login=datetime.datetime.now(datetime.UTC)
        )
        user.save()
    else:
        user.update(last_login=datetime.datetime.now(datetime.UTC))

    jwt_token = jwt.encode({
        'sub': user.google_id,
        'email': user.email,
        'exp': datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'jwt_token': jwt_token})

# Protected route for students
@app.route('/chat', methods=['POST'])
@token_required_student
def chat():
    data = request.json
    assistant_id = data.get('assistant_id')
    conversation_id = data.get('conversation_id')
    user_message = data.get('message')

    if not assistant_id or not user_message:
        return jsonify({'error': 'assistant_id and message are required'}), 400

    # Create a new conversation if conversation_id is not provided
    if not conversation_id:
        conversation = Conversation(student=g.user, assistant=Assistant.objects(id=assistant_id).first())
        conversation.save()
    else:
        conversation = Conversation.objects(id=conversation_id).first()
        if not conversation:
            return jsonify({'error': 'Invalid conversation_id'}), 400

    # Extract metadata from the current message using Utils
    metadata = Utils.extract_chat_metadata(user_message)
    refined_question = metadata['Refined Question']
    topics = metadata['Topics']
    title = metadata['Title']
    keywords = metadata['Keywords']

    # Create user message with metadata
    user_msg = UserMessage(
        message=user_message,
        refined_question=refined_question,
        topics=topics,
        title=title,
        keywords=keywords
    )

    # Add user message to conversation
    conversation.messages.append({'sender': 'user', 'content': user_msg})
    conversation.save()

    # Get embeddings for the metadata
    refined_question_embedding = Utils.get_embeddings(refined_question)
    topics_embedding = Utils.get_embeddings(", ".join(topics))
    title_embedding = Utils.get_embeddings(title)
    keywords_embedding = Utils.get_embeddings(", ".join(keywords))

    # Query Pinecone for matches
    own_matches = {
        'title': Utils.query_pinecone(assistant_id, title_embedding, 'own', 'title'),
        'topics': Utils.query_pinecone(assistant_id, topics_embedding, 'own', 'topics'),
        'keywords': Utils.query_pinecone(assistant_id, keywords_embedding, 'own', 'keywords'),
        'content': Utils.query_pinecone(assistant_id, refined_question_embedding, 'own', 'text')
    }
    supported_matches = {
        'title': Utils.query_pinecone(assistant_id, title_embedding, 'supported', 'title'),
        'topics': Utils.query_pinecone(assistant_id, topics_embedding, 'supported', 'topics'),
        'keywords': Utils.query_pinecone(assistant_id, keywords_embedding, 'supported', 'keywords'),
        'content': Utils.query_pinecone(assistant_id, refined_question_embedding, 'supported', 'text')
    }

    # Rank matches
    ranked_own_matches = Utils.rank_pinecone_matches(own_matches)
    ranked_supported_matches = Utils.rank_pinecone_matches(supported_matches)

    # Fetch original content from MongoDB
    def fetch_content(match, content_type):
        content_id, digest_id = match['content_id_digest_id'].split('__')
        content = Content.objects(id=content_id).first()
        digest = next((d for d in content.digests if str(d.id) == digest_id), None)
        return content, digest

    own_context = []
    for i, match in enumerate(ranked_own_matches):
        content, digest = fetch_content(match, 'own')
        if i < 2:
            own_context.append({
                'digest_text': digest.content,
                'parent_long_summary': content.long_summary
            })
        elif i < 5:
            own_context.append({
                'digest_long_summary': digest.long_summary,
                'parent_short_summary': content.short_summary
            })

    supported_context = []
    for i, match in enumerate(ranked_supported_matches):
        content, digest = fetch_content(match, 'supported')
        if i < 2:
            supported_context.append({
                'digest_long_summary': digest.long_summary,
                'parent_short_summary': content.short_summary
            })
        elif i < 4:
            supported_context.append({
                'digest_short_summary': digest.short_summary,
                'parent_title': content.title,
                'parent_topics': content.topics
            })

    # Generate a response using OpenAI with context
    last_two_messages = conversation.messages[-2:] if len(conversation.messages) > 1 else []
    response = Utils.generate_chat_response(user_message, conversation.conversation_summary, last_two_messages, own_context, supported_context)

    # Add assistant message to conversation
    assistant_msg = AssistantMessage(message=response, references=References(
        title_matches=own_matches['title'],
        topic_matches=own_matches['topics'],
        keyword_matches=own_matches['keywords'],
        content_matches=own_matches['content']
    ))
    conversation.messages.append({'sender': 'assistant', 'content': assistant_msg})
    conversation.save()

    # Update conversation summary
    new_summary = Utils.update_conversation_summary(conversation.conversation_summary or "", user_message, response)
    conversation.conversation_summary = new_summary
    conversation.save()

    return jsonify({
        'message': response,
        'references': {
            'own': ranked_own_matches,
            'supported': ranked_supported_matches
        }
    })

# Route to get an assistant by ID
@app.route('/get_assistant/<assistant_id>', methods=['GET'])
@token_required_teacher
def get_assistant(assistant_id):
    assistant = Assistant.objects(id=assistant_id, teacher=g.current_user).first()
    if not assistant:
        return jsonify({'error': 'Assistant not found'}), 404

    assistant_data = {
        'id': assistant.id,
        'subject': assistant.subject,
        'class_name': assistant.class_name,
        'own_content': assistant.own_content,
        'supporting_content': assistant.supporting_content,
        'allowed_students': [str(student.id) for student in assistant.allowed_students]
    }

    return jsonify({'assistant': assistant_data})

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)