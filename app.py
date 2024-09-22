from mongoengine import connect
from flask import Flask, jsonify, request, g
import jwt
from datetime import datetime, timedelta, timezone
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
from models.channel import Channel
from models.teacher import Channels


UTC = timezone.utc
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

@app.route('/create_channel', methods=['POST'])
@token_required_teacher
def create_channel():
    data = request.json
    name = data.get('name')
    profile = data.get('profile')

    if not name or not profile:
        return jsonify({'error': 'Name and profile are required'}), 400
    
    if name == "telegram":
        if not profile.get('username') or not profile.get('access_key'):
            return jsonify({'error': 'Username and access key are required for Telegram'}), 400
    elif name == "whatsapp":
        if not profile.get('phone_number') or not profile.get('app_id') or not profile.get('app_secret') or not profile.get('access_token'):
            return jsonify({'error': 'Phone number, app ID, app secret and access token are required for WhatsApp'}), 400
    elif name == "facebook":
        if not profile.get('page_id') or not profile.get('access_token'):
            return jsonify({'error': 'Page ID and access token are required for Facebook'}), 400
    elif name == "instagram":
        if not profile.get('username') or not profile.get('access_token'):
            return jsonify({'error': 'Username and access token are required for Instagram'}), 400
    else:
        return jsonify({'error': 'Invalid channel name'}), 400
    
    teacher = g.current_user
    profile['is_connected'] = True
    
    channel = Channel(
        name=name,
        profile=profile,
        teacher=teacher
    )
    channel.save()

    # Add the new channel to the appropriate list in the Channels embedded document
    if name == "telegram":
        teacher.channels.telegram.append(channel)
        Utils.connect_tg_webhook(profile.get('username'), profile.get('access_key'), channel.id)
    elif name == "whatsapp":
        teacher.channels.whatsapp.append(channel)
    elif name == "facebook":
        teacher.channels.facebook.append(channel)
    elif name == "instagram":
        teacher.channels.instagram.append(channel)

    teacher.save()

    return jsonify({'message': 'Channel created successfully', 'channel_id': channel.id})
        

@app.route('/edit_channel', methods=['POST'])
@token_required_teacher
def edit_channel():
    data = request.json
    name = data.get('name')
    profile = data.get('profile')
    id = data.get('id')

    if not name or not profile:
        return jsonify({'error': 'Name and profile are required'}), 400

    if name == "telegram":
        if not profile.get('username') or not profile.get('access_key'):
            return jsonify({'error': 'Username and access key are required for Telegram'}), 400
    elif name == "whatsapp":
        if not profile.get('phone_number') or not profile.get('app_id') or not profile.get('app_secret') or not profile.get('access_token'):
            return jsonify({'error': 'Phone number, app ID, app secret and access token are required for WhatsApp'}), 400
    elif name == "facebook":
        if not profile.get('page_id') or not profile.get('access_token'):
            return jsonify({'error': 'Page ID and access token are required for Facebook'}), 400
    elif name == "instagram":
        if not profile.get('username') or not profile.get('access_token'):
            return jsonify({'error': 'Username and access token are required for Instagram'}), 400
    else:
        return jsonify({'error': 'Invalid channel name'}), 400

    teacher = g.current_user
    channel = Channel.objects(name=name, id=id, teacher=teacher).first()
    profile['is_connected'] = True

    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    channel.profile = profile
    channel.updated_at = datetime.now(UTC)
    channel.save()

    if name == "telegram":
        Utils.connect_tg_webhook(profile.get('username'), profile.get('access_key'), channel.id)

    return jsonify({'message': 'Channel updated successfully'})        


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
    if data.get('connected_channels'):
        for channel_id in data.get('connected_channels'):
            channel = Channel.objects(id=channel_id).first()
            if channel:
                assistant.connected_channels.append(channel)
                channel.assistants.append(assistant)
                channel.save()
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
        'connected_channels': [{'id': channel.id, 'name': channel.name, 'profile': channel.profile} for channel in assistant.connected_channels],
        'allowed_students': [str(student.id) for student in assistant.allowed_students]
    }

    return jsonify({'assistant': assistant_data})

@app.route('/get_student_assistant/<assistant_id>', methods=['GET'])
@token_required_student
def get_student_assistant(assistant_id):
    assistant = Assistant.objects(id=assistant_id).first()
    student = Student.objects(id=g.current_user.id).first()
    
    if not assistant:
        return jsonify({'error': 'Assistant not found'}), 404
    if student not in assistant.allowed_students:
        return jsonify({'error': 'You are not allowed to access this assistant'}), 403

    assistant_data = {
        'id': assistant.id,
        'subject': assistant.subject,
        'class_name': assistant.class_name,
        'profile_picture': assistant.profile_picture,
        'about': assistant.about,
        'created_at': assistant.created_at,
        'updated_at': assistant.updated_at,
        'teacher': assistant.teacher.name,
        'own_content': [content.to_mongo().to_dict() for content in assistant.own_content],
        'supporting_content': [content.to_mongo().to_dict() for content in assistant.supporting_content],
    }
    return jsonify(assistant_data)

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

# Fetch original content from MongoDB
def fetch_content(match, content_type, assistant):
    content_id, digest_id = match['content_id_digest_id'].split('__')
    print(content_id, digest_id)
    # print(assistant.own_content, assistant.supporting_content)
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
    
    response, ranked_own_content, ranked_supported_content = process_chat(user_message, assistant, conversation)
    return jsonify({
        'message': response,
        'references': {
            'own': ranked_own_content,
            'supported': ranked_supported_content
        },
        'conversation_id': conversation_id
    })

def process_chat(user_message, assistant, conversation):
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
    # conversation.save()

    print("##### METADATA DONE #####")
    print(refined_question, topics, title, keywords)
    if not refined_question or not topics or not title or not keywords:
        conversation.conversation_summary = "Hello! I'm your AI assistant for your teacher. How can I help you today?"
        conversation.save()
        return "Hello! I'm your AI assistant for your teacher. How can I help you today?", [], []
    # Get embeddings for the metadata
    refined_question_embedding = Utils.get_embeddings(refined_question)
    topics_embedding = Utils.get_embeddings(", ".join(topics))
    title_embedding = Utils.get_embeddings(title)
    keywords_embedding = Utils.get_embeddings(", ".join(keywords))
    print("##### EMBEDDINGS DONE #####")

    # Query Pinecone for matches
    own_matches = {
        'title': Utils.query_pinecone(assistant.id, title_embedding, 'own', 'title'),
        'topics': Utils.query_pinecone(assistant.id, topics_embedding, 'own', 'topics'),
        'keywords': Utils.query_pinecone(assistant.id, keywords_embedding, 'own', 'keywords'),
        'content': Utils.query_pinecone(assistant.id, refined_question_embedding, 'own', 'text')
    }
    supported_matches = {
        'title': Utils.query_pinecone(assistant.id, title_embedding, 'supported', 'title'),
        'topics': Utils.query_pinecone(assistant.id, topics_embedding, 'supported', 'topics'),
        'keywords': Utils.query_pinecone(assistant.id, keywords_embedding, 'supported', 'keywords'),
        'content': Utils.query_pinecone(assistant.id, refined_question_embedding, 'supported', 'text')
    }
    print("##### PINECONE DONE #####")

    # Rank matches
    ranked_own_matches = Utils.rank_pinecone_matches(own_matches)
    ranked_supported_matches = Utils.rank_pinecone_matches(supported_matches)

    

    own_context = []
    for i, match in enumerate(ranked_own_matches):
        content, digest = fetch_content(match, 'own', assistant)
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
        content, digest = fetch_content(match, 'supported', assistant)
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
    # print(last_two_messages, own_context, supported_context)
    response = Utils.generate_chat_response(user_message, conversation.conversation_summary, last_two_messages, own_context, supported_context)
    print("##### RESPONSE DONE #####")
    print(response)
    # Add assistant message to conversation
    assistant_msg = AssistantMessage(message=response, references=References(
        own=ranked_own_matches,
        supporting=ranked_supported_matches
    ))
    conversation.messages.append(Message(sender='assistant', content=assistant_msg))
    # conversation.save()

    # Update conversation summary
    new_summary = Utils.update_conversation_summary(conversation.conversation_summary or "", user_message, response)
    conversation.conversation_summary = new_summary
    conversation.save()

    ranked_own_content = [
        {
            'content': content.to_mongo().to_dict(),
            'digest': digest.to_mongo().to_dict()
        }
        for content, digest in (fetch_content(match, 'own', assistant) for match in ranked_own_matches) if content
    ]
    ranked_supported_content = [
        {
            'content': content.to_mongo().to_dict(),
            'digest': digest.to_mongo().to_dict()
        }
        for content, digest in (fetch_content(match, 'supported', assistant) for match in ranked_supported_matches) if content
    ]
    return response, ranked_own_content, ranked_supported_content

@app.route('/get_student_assistants', methods=['GET'])
@token_required_student
def get_student_assistants():
    assistants = g.current_user.allowed_assistants
    assistants_list = [{'id': assistant.id, 'subject': assistant.subject, 'class_name': assistant.class_name, 'teacher': assistant.teacher.name, 'profile_picture': assistant.profile_picture, 'about': assistant.about} for assistant in assistants]
    return jsonify({'assistants': assistants_list})

@app.route('/get_conversations/<assistant_id>', methods=['GET'])
@token_required_student
def get_conversations(assistant_id):
    conversations = Conversation.objects(student=g.current_user, assistant=assistant_id)
    conversation_list = [
        {
            'id': conversation.id,
            'title': conversation.title or conversation.messages[0].content.title or "Untitled Conversation"
        }
        for conversation in conversations
    ]
    return jsonify({'conversations': conversation_list})

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

    # Fetch the content for the references
    ranked_own_content = [
        {
            'content': content.to_mongo().to_dict(),
            'digest': digest.to_mongo().to_dict()
        }
        for content, digest in (fetch_content(match, 'own', conversation.assistant) for match in last_assistant_message['content']['references']['own'])
    ] if last_assistant_message else []

    ranked_supported_content = [
        {
            'content': content.to_mongo().to_dict(),
            'digest': digest.to_mongo().to_dict()
        }
        for content, digest in (fetch_content(match, 'supported', conversation.assistant) for match in last_assistant_message['content']['references']['supporting'])
    ] if last_assistant_message else []
    
    return jsonify({
        'messages': messages,
        'references': {
            'own': ranked_own_content,
            'supported': ranked_supported_content
        }
    })

# Route to get teacher info
@app.route('/get_teacher_info', methods=['GET'])
@token_required_teacher
def get_teacher_info():
    teacher = g.current_user
    teacher_info = {
        'name': teacher.name,
        'profile_picture': teacher.profile_picture,
        'channels': {
            'whatsapp': {
                'profile': teacher.channels.whatsapp[0].profile,
                'id': str(teacher.channels.whatsapp[0].id)
            } if teacher.channels.whatsapp else None,
            'telegram': {
                'profile': teacher.channels.telegram[0].profile,
                'id': str(teacher.channels.telegram[0].id)
            } if teacher.channels.telegram else None,
            'facebook': {
                'profile': teacher.channels.facebook[0].profile,
                'id': str(teacher.channels.facebook[0].id)
            } if teacher.channels.facebook else None,
            'instagram': {
                'profile': teacher.channels.instagram[0].profile,
                'id': str(teacher.channels.instagram[0].id)
            } if teacher.channels.instagram else None
        }
    }
    return jsonify({'teacher': teacher_info})

@app.route('/get_student_info', methods=['GET'])
@token_required_student
def get_student_info():
    student = g.current_user
    student_info = {
        'id': student.id,
        'name': student.name,
        'profile_picture': student.profile_picture,
        'wa_number': student.wa_number or None,
        'tg_handle': student.tg_handle or None,
        'ig_handle': student.ig_handle or None,
        'fb_handle': student.fb_handle or None
    }
    return jsonify({'student': student_info})

# Route to edit an assistant
@app.route('/edit_assistant/<assistant_id>', methods=['POST'])
@token_required_teacher
def edit_assistant(assistant_id):
    data = request.json
    subject = data.get('subject')
    class_name = data.get('class_name')
    about = data.get('about')
    profile_picture = data.get('profile_picture')
    connected_channels = data.get('connected_channels')

    assistant = Assistant.objects(id=assistant_id, teacher=g.current_user).first()
    if not assistant:
        return jsonify({'error': 'Assistant not found'}), 404

    if subject:
        assistant.subject = subject
    if class_name:
        assistant.class_name = class_name
    if about:
        assistant.about = about
    if profile_picture:
        assistant.profile_picture = profile_picture
    assistant.connected_channels = []
    if connected_channels:
        print(connected_channels)
        for channel_id in connected_channels:
            channel = Channel.objects(id=channel_id).first()
            if channel:
                assistant.connected_channels.append(channel)
                if assistant not in channel.assistants:
                    channel.assistants.append(assistant)
                    channel.save()
            

    assistant.save()
    return jsonify({'message': 'Assistant updated successfully'})

@app.route('/delete_file', methods=['POST'])
@token_required_teacher
def delete_file():
    data = request.json
    assistant_id = data.get('assistant_id')
    content_id = data.get('content_id')
    content_type = data.get('content_type')

    if not assistant_id or not content_id or not content_type:
        return jsonify({'error': 'Assistant ID, content ID, and content type are required'}), 400

    assistant = Assistant.objects(id=assistant_id).first()
    if not assistant:
        return jsonify({'error': 'Assistant not found'}), 404

    if content_type == 'own':
        content_list = assistant.own_content
    else:
        content_list = assistant.supporting_content

    content_to_delete = next((content for content in content_list if content.id == content_id), None)
    if not content_to_delete:
        return jsonify({'error': 'Content not found'}), 404

    content_list.remove(content_to_delete)
    assistant.save()

    return jsonify({'message': 'Content deleted successfully'})

@app.route('/wa-webhook/<wa_id>', methods=['GET', 'POST'])
def wa_webhook(wa_id):
    try:
        if request.method == 'GET':
            challenge = request.args.get('hub.challenge')
            print(challenge)
            print(wa_id)
            return challenge, 200
        elif request.method == 'POST':
            # verify the token
            # token = request.args.get('hub.verify_token')
            # print(token)
            # if token == 'my-secret-token':
            #     challenge = request.args.get('hub.challenge')
            #     return challenge, 200
            # else:
            #     return 'Invalid token', 403
            
            data = request.json
            # print(data)

            if not data or not data.get('entry') or not data.get('entry')[0].get('changes') or not data.get('entry')[0].get('changes')[0].get('value') or not data.get('entry')[0].get('changes')[0].get('value').get('contacts') or not data.get('entry')[0].get('changes')[0].get('value').get('contacts')[0].get('profile') or not data.get('entry')[0].get('changes')[0].get('value').get('contacts')[0].get('profile').get('name') or not data.get('entry')[0].get('changes')[0].get('value').get('metadata') or not data.get('entry')[0].get('changes')[0].get('value').get('metadata').get('phone_number_id') or not data.get('entry')[0].get('changes')[0].get('value').get('messages') or not data.get('entry')[0].get('changes')[0].get('value').get('messages')[0].get('text'):
                return 'ok', 200
            
            display_phone_number = data.get('entry')[0].get('changes')[0].get('value').get('metadata').get('display_phone_number')
            print(display_phone_number)

            channel = Channel.objects(name="whatsapp", profile__phone_number=display_phone_number).first()
            assistant = channel.assistants[0] if channel and channel.assistants else None
            if not assistant:
                return 'ok', 200
            

            phone_number = data.get('entry')[0].get('changes')[0].get('value').get('contacts')[0].get('wa_id') or None
            message = data.get('entry')[0].get('changes')[0].get('value').get('messages')[0].get('text').get('body') or None
            print(phone_number, message)
            student = Student.objects(wa_number=phone_number).first()
            if not student:
                print("Student not found")
                return 'ok', 200
            if not student in assistant.allowed_students or not assistant in student.allowed_assistants:
                print("Student not allowed")
                return 'ok', 200
            
            conversation = Conversation.objects(student=student, assistant=assistant).first()
            if not conversation:
                conversation = Conversation(student=student, assistant=assistant)
                conversation.save()

            # get user name
            user_name = data.get('entry')[0].get('changes')[0].get('value').get('contacts')[0].get('profile').get('name') or None
            print(user_name)

            print("Here...")
            
            # Send a message to the user
            sender_id = data.get('entry')[0].get('changes')[0].get('value').get('metadata').get('phone_number_id') or None
            sender_access_token = channel.profile.get('access_token') if channel.profile.get('access_token') else None
            if not sender_id or not sender_access_token:
                print("Sender ID or Sender Access Token not found")
                return 'ok', 200


            print(sender_id, sender_access_token, phone_number, message)
            res_message, ranked_own_content, ranked_supported_content = process_chat(message, assistant, conversation)
            if ranked_own_content or ranked_supported_content:
                reply = '*Answer :* ' + res_message + '\n\n*Teacher References :* \n'
                for i, content in enumerate(ranked_own_content[:4]):
                    reply += f'{content.get("content").get("fileUrl")}\n'
                reply += '\n\n*Supporting References :* \n'
                for i, content in enumerate(ranked_supported_content[:4]):
                    reply += f'{content.get("content").get("fileUrl")}\n'
            else:
                reply = res_message or "Sorry, I'm not able to answer that."

            if sender_id and sender_access_token and phone_number and message:
                Utils.send_wa_message(sender_id, phone_number, reply, sender_access_token)
                print("Message sent")
            return 'ok', 200
    except Exception as e:
        print(e)
        return 'ok', 200
    
@app.route('/telegram-webhook/<channel_id>', methods=['GET', 'POST'])
def telegram_webhook(channel_id):
    data = request.json
    channel = Channel.objects(id=channel_id).first()
    if not channel:
        print("Channel not found")
        return 'ok', 200
    assistant = channel.assistants[0] if channel.assistants else None
    if not assistant:
        print("Assistant not found")
        return 'ok', 200
    student = Student.objects(tg_handle=data.get('message').get('from').get('username')).first()
    if not student:
        print("Student not found")
        return 'ok', 200
    if not student in assistant.allowed_students or not assistant in student.allowed_assistants:
        print("Student not allowed")
        return 'ok', 200
    
    conversation = Conversation.objects(student=student, assistant=assistant).first()
    if not conversation:
        conversation = Conversation(student=student, assistant=assistant)
        conversation.save()
    
    message = data.get('message').get('text')
    chat_id = data.get('message').get('chat').get('id')
    print(message)
    if message.startswith('/'):
        command = message.split(' ')[0][1:]
        if command == 'help':
            reply = "Here are the commands you can use:\n\n/help - Show this message\n/start - Start a new conversation\n/stop - Stop the current conversation"
            Utils.send_tg_message(channel.profile.get('access_key'), chat_id, reply)
            return 'ok', 200
        elif command == 'start':
            conversation = Conversation(student=student, assistant=assistant)
            conversation.save()
            reply = "Welcome to " + assistant.teacher.name + "'s chat! How can I help you today?"
            Utils.send_tg_message(channel.profile.get('access_key'), chat_id, reply)
            return 'ok', 200
        elif command == 'stop':
            conversation.delete()
            reply = "Conversation stopped. How can I help you today?"
            Utils.send_tg_message(channel.profile.get('access_key'), chat_id, reply)
            return 'ok', 200
        else:
            reply = "Sorry, I'm not able to answer that."
            Utils.send_tg_message(channel.profile.get('access_key'), chat_id, reply)
            return 'ok', 200
    res_message, ranked_own_content, ranked_supported_content = process_chat(message, assistant, conversation)
    print(res_message, ranked_own_content, ranked_supported_content)
    
    if ranked_own_content or ranked_supported_content:
        reply = '*Answer :* ' + res_message + '\n\n*Teacher References :* \n'
        for i, content in enumerate(ranked_own_content[:4]):
            reply += f'{content.get("content").get("fileUrl")}\n'
        reply += '\n\n*Supporting References :* \n'
        for i, content in enumerate(ranked_supported_content[:4]):
            reply += f'{content.get("content").get("fileUrl")}\n'
    else:
        reply = res_message or "Sorry, I'm not able to answer that."

    if message:
        Utils.send_tg_message(channel.profile.get('access_key'), chat_id, reply)
        print("Message sent")
    return 'ok', 200

@app.route('/update_student_wa', methods=['POST'])
@token_required_student
def update_student_wa():
    data = request.json
    wa_number = data.get('wa_number')
    tg_handle = data.get('tg_handle')
    ig_handle = data.get('ig_handle')
    fb_handle = data.get('fb_handle')

    
    student = g.current_user
    if wa_number:
        student.wa_number = wa_number
    if tg_handle:
        student.tg_handle = tg_handle
    if ig_handle:
        student.ig_handle = ig_handle
    if fb_handle:
        student.fb_handle = fb_handle
    
    student.save()

    return jsonify({'message': 'Student updated successfully'})


# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)