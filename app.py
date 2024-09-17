from mongoengine import connect
from flask import Flask, jsonify, request, g
import jwt
from datetime import datetime, UTC, timedelta
from models.teacher import Teacher
from middlewares.authentication import token_required_teacher, token_required_student
from dotenv import load_dotenv
load_dotenv()
from flask_cors import CORS
from services.google_login import GoogleLogin 
import os
from models.assistant import Assistant, Content, DigestedContent
from models.student import Student
from models.conversation import Conversation, UserMessage, AssistantMessage, References, Message
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
            created_at=datetime.now(UTC),
            last_login=datetime.now(UTC)
        )
        user.save()
    else:
        user.update(last_login=datetime.now(UTC))

    jwt_token = jwt.encode({
        'sub': user.google_id,
        'email': user.email,
        'exp': datetime.now(UTC) + timedelta(days=30)
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
    if data.get('profile_picture'):
        assistant.profile_picture = data.get('profile_picture')
    if data.get('about'):
        assistant.about = data.get('about')
    assistant.created_at = datetime.now(UTC)
    assistant.save()

    return jsonify({'message': 'Assistant created successfully', 'assistant_id': assistant.id})

@app.route('/add_student_to_assistant', methods=['POST'])
@token_required_teacher
def add_student_to_assistant():
    data = request.json
    student_id = data.get('student_id')
    assistant_id = data.get('assistant_id')

    if not student_id or not assistant_id:
        return jsonify({'error': 'Student ID and assistant ID are required'}), 400

    student = Student.objects(id=student_id).first()
    assistant = Assistant.objects(id=assistant_id).first()
    
    if not student or not assistant:
        return jsonify({'error': 'Student or assistant not found'}), 404

    if student in assistant.allowed_students:
        return jsonify({'error': 'Student already in assistant'}), 400
    assistant.allowed_students.append(student)
    assistant.save()
    student.allowed_assistants.append(assistant)
    student.save()

    return jsonify({'message': 'Student added to assistant successfully'})

@app.route('/remove_student_from_assistant', methods=['POST'])
@token_required_teacher
def remove_student_from_assistant():
    data = request.json
    student_id = data.get('student_id')
    assistant_id = data.get('assistant_id')

    if not student_id or not assistant_id:
        return jsonify({'error': 'Student ID and assistant ID are required'}), 400

    student = Student.objects(id=student_id).first()
    assistant = Assistant.objects(id=assistant_id).first()
    
    if not student or not assistant:
        return jsonify({'error': 'Student or assistant not found'}), 404

    if student in assistant.allowed_students:
        assistant.allowed_students.remove(student)
        assistant.save()
    if assistant in student.allowed_assistants:
        student.allowed_assistants.remove(assistant)
        student.save()

    return jsonify({'message': 'Student removed from assistant successfully'})

# Route to get all assistants for a teacher
@app.route('/get_assistants', methods=['GET'])
@token_required_teacher
def get_assistants():
    assistants = Assistant.objects(teacher=g.current_user)
    assistants_list = [
        {
            'id': assistant.id,
            'subject': assistant.subject,
            'class_name': assistant.class_name,
            'profile_picture': assistant.profile_picture,
            'about': assistant.about,
            'created_at': assistant.created_at,
            'updated_at': assistant.updated_at
        }
        for assistant in assistants
    ]

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
        print("##### SUMMARIES DONE #####")
        metadata = Utils.get_metadata(long_summary)
        print("##### METADATA DONE #####")

        content = Content(
            file_type=file_type,
            content=text_content,
            fileUrl=fileUrl,
            title=metadata['Title'],
            topics=metadata['Topics'],
            keywords=metadata['Keywords'],
            short_summary=short_summary,
            long_summary=long_summary
        )
        
        chunks = Utils.create_chunks(text_content)
        print("##### CHUNKS DONE #####")
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
            'content': content.to_mongo().to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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
        'profile_picture': assistant.profile_picture,
        'about': assistant.about,
        'created_at': assistant.created_at,
        'updated_at': assistant.updated_at,
        'own_content': [content.to_mongo().to_dict() for content in assistant.own_content],
        'supporting_content': [content.to_mongo().to_dict() for content in assistant.supporting_content],
        'allowed_students': [str(student.id) for student in assistant.allowed_students]
    }

    return jsonify({'assistant': assistant_data})


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
            created_at=datetime.now(datetime.UTC),
            last_login=datetime.now(datetime.UTC)
        )
        user.save()
    else:
        user.update(last_login=datetime.now(datetime.UTC))

    jwt_token = jwt.encode({
        'sub': user.google_id,
        'email': user.email,
        'exp': datetime.now(datetime.UTC) + timedelta(days=30)
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
        conversation = Conversation(
            student=g.current_user,
            assistant=Assistant.objects(id=assistant_id).first()
        )
        conversation.save()
        conversation_id = conversation.id
    else:
        conversation = Conversation.objects(id=conversation_id).first()
        if not conversation:
            return jsonify({'error': 'Invalid conversation_id'}), 400

    assistant = Assistant.objects(id=assistant_id).first()
    if not assistant:
        return jsonify({'error': 'Invalid assistant_id'}), 400
    
    # Extract metadata from the current message using Utils
    metadata = Utils.extract_chat_metadata(user_message)
    refined_question = metadata['RefinedQuestion']
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
    conversation.messages.append(Message(sender='user', content=user_msg))
    conversation.save()

    # Get embeddings for the metadata
    refined_question_embedding = Utils.get_embeddings(refined_question)
    topics_embedding = Utils.get_embeddings(", ".join(topics))
    title_embedding = Utils.get_embeddings(title)
    keywords_embedding = Utils.get_embeddings(", ".join(keywords))
    print("##### EMBEDDINGS DONE #####")

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
    print("##### PINECONE DONE #####")

    # Rank matches
    ranked_own_matches = Utils.rank_pinecone_matches(own_matches)
    ranked_supported_matches = Utils.rank_pinecone_matches(supported_matches)

    # Fetch original content from MongoDB
    def fetch_content(match, content_type):
        content_id, digest_id = match['content_id_digest_id'].split('__')
        print(content_id, digest_id)
        print(assistant.own_content, assistant.supporting_content)
        if content_type == 'own':
            content = next((c for c in assistant.own_content if c.id == content_id), None)
        else:
            content = next((c for c in assistant.supporting_content if c.id == content_id), None)
        
        if content:
            digest = next((d for d in content.digests if str(d.id) == digest_id), None)
        else:
            digest = None
        
        print("##### FETCHED CONTENT #####")
        return content, digest

    own_context = []
    for i, match in enumerate(ranked_own_matches):
        content, digest = fetch_content(match, 'own')
        if i < 2:
            own_context.append({
                'digest_text': digest.content or "",
                'parent_long_summary': content.long_summary or ""
            })
        elif i < 5:
            own_context.append({
                'digest_long_summary': digest.long_summary or "",
                'parent_short_summary': content.short_summary or ""
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
    print(last_two_messages, own_context, supported_context)
    response = Utils.generate_chat_response(user_message, conversation.conversation_summary, last_two_messages, own_context, supported_context)
    print("##### RESPONSE DONE #####")
    print(response)
    # Add assistant message to conversation
    assistant_msg = AssistantMessage(message=response, references=References(
        own=ranked_own_matches,
        supporting=ranked_supported_matches
    ))
    conversation.messages.append(Message(sender='assistant', content=assistant_msg))
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
        },
        'conversation_id': conversation_id
    })

@app.route('/get_student_assistants', methods=['GET'])
@token_required_student
def get_student_assistants():
    assistants = g.current_user.allowed_assistants
    assistants_list = [{'id': assistant.id, 'subject': assistant.subject, 'class_name': assistant.class_name, 'teacher': assistant.teacher.name} for assistant in assistants]
    return jsonify({'assistants': assistants_list})

@app.route('/get_conversation/<conversation_id>', methods=['GET'])
@token_required_student
def get_conversation(conversation_id):
    conversation = Conversation.objects(id=conversation_id, student=g.current_user).first()
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    messages = [
        {
            'sender': message.sender,
            'content': message.content.message if message.sender == 'user' else message.content.message,
            'references':  [ref for ref in message.content.references] if message.sender == 'assistant' else None
        }
        for message in conversation.messages
    ]

    # Find the last assistant message
    last_assistant_message = (next((msg for msg in reversed(conversation.messages) if msg.sender == 'assistant'), None)).to_mongo().to_dict()

    return jsonify({
        'messages': messages,
        'references': {
            'own': last_assistant_message['content']['references']['own'] if last_assistant_message else [],
            'supported': last_assistant_message['content']['references']['supporting'] if last_assistant_message else []
        }
    })

# Route to get teacher info
@app.route('/get_teacher_info', methods=['GET'])
@token_required_teacher
def get_teacher_info():
    teacher = g.current_user
    teacher_info = {
        'name': teacher.name,
        'profile_picture': teacher.profile_picture
    }
    return jsonify({'teacher': teacher_info})

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)