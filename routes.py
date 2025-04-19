"""
Routes for the Photo Sharing Application
"""

import os
import uuid
import json
import logging
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, session, jsonify, abort, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func
from app import app, db, csrf_protected, login_required
from models import User, Photo, Room, RoomMember, PhotoTag, ShareableLink, Analytics, FaceRecognitionSettings, Album

# Setup logging
logger = logging.getLogger(__name__)

# Helper function to check if a file has an allowed extension
def is_allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to get the current logged in user
def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# Helper function to track analytics
def track_analytics(room_id, event_type, event_data=None, photo_id=None):
    try:
        analytics = Analytics(
            room_id=room_id,
            event_type=event_type,
            event_data=json.dumps(event_data) if event_data else None,
            user_id=session.get('user_id'),
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(analytics)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error tracking analytics: {str(e)}")

# Helper function to check if the current user can access a room
def can_access_room(room_id):
    """Check if the current user can access the room"""
    # Get the room
    room = Room.query.get(room_id)
    if not room:
        return False
    
    # Admin/creator always has access
    current_user = get_current_user()
    if current_user and (current_user.id == room.creator_id):
        return True
    
    # Room members have access
    if current_user:
        member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
        if member:
            return True
    
    # Public rooms are accessible to everyone
    if room.is_public:
        return True
    
    # Check if user has access via access code
    if 'room_access_codes' in session and str(room_id) in session['room_access_codes']:
        return True
    
    return False

# Home page route
@app.route('/')
def index():
    return render_template('index.html')

# User registration
@app.route('/register', methods=['GET', 'POST'])
@csrf_protected
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Basic validation
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        password_hash = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=password_hash)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {str(e)}")
            flash('An error occurred during registration', 'danger')
    
    return render_template('register.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
@csrf_protected
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

# User logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Create a new room
@app.route('/room/create', methods=['GET', 'POST'])
@login_required
@csrf_protected
def create_room():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = request.form.get('is_public') == 'true'
        
        # Generate a random access code for private rooms
        access_code = None
        if not is_public:
            access_code = ''.join(str(uuid.uuid4()).split('-')[0:2])
        
        # Create new room
        new_room = Room(
            name=name,
            description=description,
            creator_id=session['user_id'],
            is_public=is_public,
            access_code=access_code,
            face_recognition_enabled=True
        )
        
        try:
            db.session.add(new_room)
            db.session.commit()
            
            # Add creator as a room member with admin role
            member = RoomMember(
                room_id=new_room.id,
                user_id=session['user_id'],
                role='admin'
            )
            db.session.add(member)
            db.session.commit()
            
            flash('Room created successfully!', 'success')
            return redirect(url_for('room', room_id=new_room.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating room: {str(e)}")
            flash('An error occurred while creating the room', 'danger')
    
    return render_template('create_room.html')

# View room and its photos
@app.route('/room/<int:room_id>')
def room(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user can access this room
    if not can_access_room(room_id):
        flash('You do not have access to this room', 'danger')
        return redirect(url_for('join_room'))
    
    # Track room view analytics
    track_analytics(room_id, 'room_view')
    
    # Get all photos in the room
    photos = Photo.query.filter_by(room_id=room_id).order_by(Photo.uploaded_at.desc()).all()
    
    # Get all available albums in the room
    albums = Album.query.filter_by(room_id=room_id).all()
    
    # Check if user is a member/admin
    current_user = get_current_user()
    is_member = False
    is_admin = False
    
    if current_user:
        member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
        is_member = member is not None
        is_admin = member.role == 'admin' if member else False
    
    return render_template(
        'room.html',
        room=room,
        photos=photos,
        albums=albums,
        is_member=is_member,
        is_admin=is_admin
    )

# Enter room access code
@app.route('/room/<int:room_id>/access', methods=['GET', 'POST'])
@csrf_protected
def room_access(room_id):
    room = Room.query.get_or_404(room_id)
    
    # If room is public or user already has access, redirect to room
    if room.is_public or can_access_room(room_id):
        return redirect(url_for('room', room_id=room_id))
    
    if request.method == 'POST':
        access_code = request.form.get('access_code')
        
        if access_code == room.access_code:
            # Store access code in session
            if 'room_access_codes' not in session:
                session['room_access_codes'] = {}
            
            session['room_access_codes'][str(room_id)] = access_code
            
            flash('Access granted!', 'success')
            return redirect(url_for('room', room_id=room_id))
        else:
            flash('Invalid access code', 'danger')
    
    return render_template('room_access.html', room=room)

# Upload photo to a room
@app.route('/room/<int:room_id>/upload', methods=['GET', 'POST'])
@csrf_protected
def upload_photo(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user can access this room
    if not can_access_room(room_id):
        flash('You do not have access to this room', 'danger')
        return redirect(url_for('join_room'))
    
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'photo' not in request.files:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'No file part'}), 400
            flash('No file part', 'danger')
            return redirect(request.url)
        
        # Handle both single and multiple file uploads
        files = request.files.getlist('photo')
        
        if not files or files[0].filename == '':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'No selected file'}), 400
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        # Create upload folder for this room if it doesn't exist
        room_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(room_id))
        if not os.path.exists(room_upload_folder):
            os.makedirs(room_upload_folder)
        
        # Get description from form if available
        description = request.form.get('description', '')
        
        # Track successful uploads
        successful_uploads = []
        failed_uploads = []
        
        # Process each file
        for file in files:
            if file and is_allowed_file(file.filename):
                try:
                    # Generate a safe filename
                    original_filename = secure_filename(file.filename)
                    filename = f"{uuid.uuid4().hex}_{original_filename}"
                    
                    # Save the file
                    file_path = os.path.join(room_upload_folder, filename)
                    file.save(file_path)
                    
                    # Create new photo record
                    new_photo = Photo(
                        filename=filename,
                        original_filename=original_filename,
                        user_id=session.get('user_id', 1),  # Default to user 1 if no user logged in
                        room_id=room_id,
                        description=description
                    )
                    
                    db.session.add(new_photo)
                    db.session.commit()
                    
                    # Process with face recognition if enabled
                    if room.face_recognition_enabled:
                        from face_recognition_utils import process_photo_face_recognition
                        process_photo_face_recognition(new_photo.id, file_path)
                    
                    successful_uploads.append({
                        'filename': original_filename,
                        'id': new_photo.id,
                        'url': url_for('view_photo', photo_id=new_photo.id)
                    })
                
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error uploading photo {file.filename}: {str(e)}")
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': str(e)
                    })
            else:
                failed_uploads.append({
                    'filename': file.filename,
                    'error': 'File type not allowed'
                })
        
        # Return appropriate response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': len(successful_uploads) > 0,
                'total': len(files),
                'successful': len(successful_uploads),
                'failed': len(failed_uploads),
                'uploads': successful_uploads,
                'errors': failed_uploads
            })
        
        # Flash appropriate messages for regular form submissions
        if successful_uploads:
            if len(failed_uploads) > 0:
                flash(f'Uploaded {len(successful_uploads)} photos successfully. {len(failed_uploads)} photos failed.', 'info')
            else:
                flash(f'Successfully uploaded {len(successful_uploads)} photos!', 'success')
            return redirect(url_for('room', room_id=room_id))
        else:
            flash('No photos were uploaded. Please check file types and try again.', 'danger')
            return redirect(request.url)
    
    return render_template('upload_photo.html', room=room)

# View a single photo
@app.route('/photo/<int:photo_id>')
def view_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Check if user can access the room this photo belongs to
    if not can_access_room(photo.room_id):
        flash('You do not have access to this photo', 'danger')
        return redirect(url_for('join_room'))
    
    # Track photo view analytics
    track_analytics(photo.room_id, 'photo_view', {'photo_id': photo_id})
    
    # Get all tags for this photo
    tags = PhotoTag.query.filter_by(photo_id=photo_id).all()
    
    # Get the room
    room = Room.query.get(photo.room_id)
    
    return render_template('view_photo.html', photo=photo, room=room, tags=tags)

# Download a photo
@app.route('/photo/<int:photo_id>/download')
def download_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Check if user can access the room this photo belongs to
    if not can_access_room(photo.room_id):
        flash('You do not have access to this photo', 'danger')
        return redirect(url_for('join_room'))
    
    # Update download count
    photo.download_count += 1
    db.session.commit()
    
    # Track download analytics
    track_analytics(photo.room_id, 'photo_download', {'photo_id': photo_id})
    
    # Get file path
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(photo.room_id), photo.filename)
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=photo.original_filename
    )

# Join a room with access code
@app.route('/join-room', methods=['GET', 'POST'])
@csrf_protected
def join_room():
    if request.method == 'POST':
        access_code = request.form.get('access_code')
        
        # Find room with this access code
        room = Room.query.filter_by(access_code=access_code).first()
        
        if room:
            # Store access code in session
            if 'room_access_codes' not in session:
                session['room_access_codes'] = {}
            
            session['room_access_codes'][str(room.id)] = access_code
            
            # If user is logged in, add them as a member
            current_user = get_current_user()
            if current_user:
                # Check if already a member
                existing_member = RoomMember.query.filter_by(
                    room_id=room.id,
                    user_id=current_user.id
                ).first()
                
                if not existing_member:
                    new_member = RoomMember(
                        room_id=room.id,
                        user_id=current_user.id,
                        role='member'
                    )
                    db.session.add(new_member)
                    db.session.commit()
            
            flash('Room joined successfully!', 'success')
            return redirect(url_for('room', room_id=room.id))
        else:
            flash('Invalid access code', 'danger')
    
    # Get list of public rooms
    public_rooms = Room.query.filter_by(is_public=True).order_by(Room.created_at.desc()).all()
    
    return render_template('join_room.html', public_rooms=public_rooms)

# Create shareable link for a room
@app.route('/room/<int:room_id>/share', methods=['GET', 'POST'])
@login_required
@csrf_protected
def share_room(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user is the creator or an admin
    current_user = get_current_user()
    member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    
    if not (current_user.id == room.creator_id or (member and member.role == 'admin')):
        flash('You do not have permission to share this room', 'danger')
        return redirect(url_for('room', room_id=room_id))
    
    if request.method == 'POST':
        expires_in_days = request.form.get('expires_in_days')
        
        try:
            expires_in_days = int(expires_in_days) if expires_in_days else None
            
            # Create the shareable link
            shareable_link = ShareableLink(
                room_id=room_id,
                created_by=current_user.id,
                expires_in_days=expires_in_days
            )
            
            db.session.add(shareable_link)
            db.session.commit()
            
            flash('Shareable link created successfully!', 'success')
            return redirect(url_for('share_room', room_id=room_id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating shareable link: {str(e)}")
            flash('An error occurred while creating the shareable link', 'danger')
    
    # Get all active shareable links for this room
    active_links = ShareableLink.query.filter_by(
        room_id=room_id,
        is_active=True
    ).order_by(ShareableLink.created_at.desc()).all()
    
    # Remove expired links from the active list
    valid_links = []
    for link in active_links:
        if not link.is_expired():
            valid_links.append(link)
        elif link.is_active:
            # Deactivate expired links
            link.is_active = False
            db.session.commit()
    
    return render_template('share_room.html', room=room, links=valid_links)

# Access room via shareable link
@app.route('/s/<token>')
def access_shared_link(token):
    # Find the link
    link = ShareableLink.query.filter_by(token=token).first_or_404()
    
    # Check if link is active and not expired
    if not link.is_active or link.is_expired():
        flash('This link has expired or been deactivated', 'danger')
        return redirect(url_for('index'))
    
    # Increment access count
    link.access_count += 1
    db.session.commit()
    
    # Track link access analytics
    track_analytics(link.room_id, 'link_access', {'link_id': link.id})
    
    # Grant access to the room via session
    if 'room_access_codes' not in session:
        session['room_access_codes'] = {}
    
    room = Room.query.get(link.room_id)
    if room and room.access_code:
        session['room_access_codes'][str(link.room_id)] = room.access_code
    
    return redirect(url_for('room', room_id=link.room_id))

# Deactivate a shareable link
@app.route('/link/<int:link_id>/deactivate')
@login_required
def deactivate_link(link_id):
    link = ShareableLink.query.get_or_404(link_id)
    
    # Check if user is the creator of the link or room admin
    current_user = get_current_user()
    if not (current_user.id == link.created_by or current_user.id == link.room.creator_id):
        flash('You do not have permission to deactivate this link', 'danger')
        return redirect(url_for('share_room', room_id=link.room_id))
    
    # Deactivate the link
    link.is_active = False
    db.session.commit()
    
    flash('Link deactivated successfully', 'success')
    return redirect(url_for('share_room', room_id=link.room_id))

# User dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    current_user = get_current_user()
    
    # Get all rooms where user is member or creator
    user_rooms = Room.query.join(RoomMember).filter(
        (Room.creator_id == current_user.id) | 
        (RoomMember.user_id == current_user.id)
    ).distinct().all()
    
    # Get total photos
    total_photos = Photo.query.join(Room).join(RoomMember).filter(
        (Room.creator_id == current_user.id) | 
        (RoomMember.user_id == current_user.id)
    ).count()
    
    # Get analytics data
    # Views per room
    room_views = {}
    room_downloads = {}
    
    for room in user_rooms:
        # Count view events
        views = Analytics.query.filter_by(
            room_id=room.id,
            event_type='room_view'
        ).count()
        
        room_views[room.id] = views
        
        # Count download events
        downloads = Analytics.query.filter_by(
            room_id=room.id,
            event_type='photo_download'
        ).count()
        
        room_downloads[room.id] = downloads
    
    # Total views and downloads
    total_views = sum(room_views.values())
    total_downloads = sum(room_downloads.values())
    
    # Get activity data for last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Generate date labels
    date_labels = []
    current_date = start_date
    while current_date <= end_date:
        date_labels.append(current_date.strftime('%m/%d'))
        current_date += timedelta(days=1)
    
    # Collect view and download counts per day
    view_counts = []
    download_counts = []
    
    for i in range(len(date_labels)):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        # Get all room IDs where user is member or creator
        room_ids = [room.id for room in user_rooms]
        
        # Count view events for this day
        day_views = Analytics.query.filter(
            Analytics.room_id.in_(room_ids),
            Analytics.event_type == 'room_view',
            Analytics.timestamp >= day_start,
            Analytics.timestamp < day_end
        ).count()
        
        view_counts.append(day_views)
        
        # Count download events for this day
        day_downloads = Analytics.query.filter(
            Analytics.room_id.in_(room_ids),
            Analytics.event_type == 'photo_download',
            Analytics.timestamp >= day_start,
            Analytics.timestamp < day_end
        ).count()
        
        download_counts.append(day_downloads)
    
    return render_template(
        'dashboard.html',
        rooms=user_rooms,
        total_photos=total_photos,
        total_views=total_views,
        total_downloads=total_downloads,
        room_views=room_views,
        room_downloads=room_downloads,
        date_labels=date_labels,
        view_counts=view_counts,
        download_counts=download_counts
    )

# Room analytics
@app.route('/room/<int:room_id>/analytics')
@login_required
def room_analytics(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user is the creator or an admin
    current_user = get_current_user()
    member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    
    if not (current_user.id == room.creator_id or (member and member.role == 'admin')):
        flash('You do not have permission to view analytics for this room', 'danger')
        return redirect(url_for('room', room_id=room_id))
    
    # Get basic stats
    photo_count = Photo.query.filter_by(room_id=room_id).count()
    view_count = Analytics.query.filter_by(room_id=room_id, event_type='room_view').count()
    download_count = Analytics.query.filter_by(room_id=room_id, event_type='photo_download').count()
    link_access_count = Analytics.query.filter_by(room_id=room_id, event_type='link_access').count()
    
    # Most viewed photos
    most_viewed_photo_stats = db.session.query(
        Photo,
        func.count(Analytics.id).label('view_count')
    ).join(
        Analytics,
        db.and_(
            Analytics.event_type == 'photo_view',
            Analytics.event_data.like(f'%"photo_id": {Photo.id}%')
        )
    ).filter(
        Photo.room_id == room_id
    ).group_by(
        Photo.id
    ).order_by(
        func.count(Analytics.id).desc()
    ).limit(5).all()
    
    # Most downloaded photos
    most_downloaded_photos = db.session.query(
        Photo
    ).filter(
        Photo.room_id == room_id
    ).order_by(
        Photo.download_count.desc()
    ).limit(5).all()
    
    # Get active links for the room
    active_links = ShareableLink.query.filter_by(
        room_id=room_id,
        is_active=True
    ).all()
    
    # Time series data for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Generate date labels
    date_labels = []
    current_date = start_date
    while current_date <= end_date:
        date_labels.append(current_date.strftime('%m/%d'))
        current_date += timedelta(days=1)
    
    # Collect view and download counts per day
    view_counts = []
    download_counts = []
    
    for i in range(len(date_labels)):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        # Count view events for this day
        day_views = Analytics.query.filter(
            Analytics.room_id == room_id,
            Analytics.event_type == 'room_view',
            Analytics.timestamp >= day_start,
            Analytics.timestamp < day_end
        ).count()
        
        view_counts.append(day_views)
        
        # Count download events for this day
        day_downloads = Analytics.query.filter(
            Analytics.room_id == room_id,
            Analytics.event_type == 'photo_download',
            Analytics.timestamp >= day_start,
            Analytics.timestamp < day_end
        ).count()
        
        download_counts.append(day_downloads)
    
    return render_template(
        'analytics.html',
        room=room,
        photo_count=photo_count,
        view_count=view_count,
        download_count=download_count,
        link_access_count=link_access_count,
        most_viewed_photos=most_viewed_photo_stats,
        most_downloaded_photos=most_downloaded_photos,
        active_links=active_links,
        date_labels=date_labels,
        view_counts=view_counts,
        download_counts=download_counts
    )

# Face recognition settings
@app.route('/face-recognition-settings', methods=['GET', 'POST'])
@login_required
@csrf_protected
def face_recognition_settings():
    if request.method == 'POST':
        min_confidence = float(request.form.get('min_confidence', 0.6))
        detection_algorithm = request.form.get('detection_algorithm', 'hog')
        face_encoding_model = request.form.get('face_encoding_model', 'small')
        auto_categorize = request.form.get('auto_categorize') == 'on'
        recognition_tolerance = float(request.form.get('recognition_tolerance', 0.6))
        
        try:
            # Get or create settings
            settings = FaceRecognitionSettings.query.first()
            if not settings:
                settings = FaceRecognitionSettings()
                db.session.add(settings)
            
            # Update settings
            settings.min_confidence = min_confidence
            settings.detection_algorithm = detection_algorithm
            settings.face_encoding_model = face_encoding_model
            settings.auto_categorize = auto_categorize
            settings.recognition_tolerance = recognition_tolerance
            settings.last_updated = datetime.utcnow()
            
            db.session.commit()
            flash('Face recognition settings updated successfully!', 'success')
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating face recognition settings: {str(e)}")
            flash('An error occurred while updating settings', 'danger')
    
    # Get current settings
    from face_recognition_utils import get_face_settings
    settings = get_face_settings()
    
    # Get user's rooms for reprocessing
    current_user = get_current_user()
    user_rooms = Room.query.filter_by(creator_id=current_user.id).all()
    
    return render_template('face_recognition_settings.html', settings=settings, rooms=user_rooms)

# Toggle face recognition for a room
@app.route('/room/<int:room_id>/toggle-face-recognition')
@login_required
def toggle_face_recognition(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user is the creator or an admin
    current_user = get_current_user()
    if current_user.id != room.creator_id:
        flash('You do not have permission to change this setting', 'danger')
        return redirect(url_for('room', room_id=room_id))
    
    # Toggle the setting
    room.face_recognition_enabled = not room.face_recognition_enabled
    db.session.commit()
    
    status = 'enabled' if room.face_recognition_enabled else 'disabled'
    flash(f'Face recognition {status} for this room', 'success')
    
    return redirect(url_for('room', room_id=room_id))

# Create a new album in a room
@app.route('/room/<int:room_id>/album/create', methods=['GET', 'POST'])
@login_required
@csrf_protected
def create_album(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user can access this room
    if not can_access_room(room_id):
        flash('You do not have access to this room', 'danger')
        return redirect(url_for('join_room'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        
        if not name:
            flash('Album name is required', 'danger')
            return redirect(url_for('create_album', room_id=room_id))
        
        # Create new album
        new_album = Album(
            name=name,
            room_id=room_id,
            is_auto_generated=False
        )
        
        try:
            db.session.add(new_album)
            db.session.commit()
            flash('Album created successfully!', 'success')
            return redirect(url_for('room', room_id=room_id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating album: {str(e)}")
            flash('An error occurred while creating the album', 'danger')
    
    return render_template('create_album.html', room=room)

# Move photo to album
@app.route('/photo/<int:photo_id>/move-to-album', methods=['POST'])
@login_required
@csrf_protected
def move_to_album(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Check if user can access the room this photo belongs to
    if not can_access_room(photo.room_id):
        flash('You do not have access to this photo', 'danger')
        return redirect(url_for('join_room'))
    
    album_id = request.form.get('album_id')
    
    if album_id == '0':
        # Remove from album
        photo.album_id = None
        db.session.commit()
        flash('Photo removed from album', 'success')
    else:
        # Check if album exists and belongs to the same room
        album = Album.query.get(album_id)
        if not album or album.room_id != photo.room_id:
            flash('Invalid album selected', 'danger')
            return redirect(url_for('view_photo', photo_id=photo_id))
        
        # Move photo to album
        photo.album_id = album.id
        db.session.commit()
        flash('Photo moved to album successfully', 'success')
    
    return redirect(url_for('view_photo', photo_id=photo_id))

# View album
@app.route('/album/<int:album_id>')
def view_album(album_id):
    album = Album.query.get_or_404(album_id)
    
    # Check if user can access the room this album belongs to
    if not can_access_room(album.room_id):
        flash('You do not have access to this album', 'danger')
        return redirect(url_for('join_room'))
    
    # Get all photos in the album
    photos = Photo.query.filter_by(album_id=album_id).order_by(Photo.uploaded_at.desc()).all()
    
    # Get the room
    room = Room.query.get(album.room_id)
    
    return render_template('view_album.html', album=album, room=room, photos=photos)

# API endpoint for room analytics
@app.route('/api/room/<int:room_id>/analytics')
@login_required
def api_room_analytics(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user is the creator or an admin
    current_user = get_current_user()
    member = RoomMember.query.filter_by(room_id=room_id, user_id=current_user.id).first()
    
    if not (current_user.id == room.creator_id or (member and member.role == 'admin')):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get time range from query parameters
    days = request.args.get('days', 30, type=int)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Generate date labels
    date_labels = []
    current_date = start_date
    while current_date <= end_date:
        date_labels.append(current_date.strftime('%m/%d'))
        current_date += timedelta(days=1)
    
    # Collect view and download counts per day
    view_counts = []
    download_counts = []
    
    for i in range(len(date_labels)):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        # Count view events for this day
        day_views = Analytics.query.filter(
            Analytics.room_id == room_id,
            Analytics.event_type == 'room_view',
            Analytics.timestamp >= day_start,
            Analytics.timestamp < day_end
        ).count()
        
        view_counts.append(day_views)
        
        # Count download events for this day
        day_downloads = Analytics.query.filter(
            Analytics.room_id == room_id,
            Analytics.event_type == 'photo_download',
            Analytics.timestamp >= day_start,
            Analytics.timestamp < day_end
        ).count()
        
        download_counts.append(day_downloads)
    
    return jsonify({
        'date_labels': date_labels,
        'view_counts': view_counts,
        'download_counts': download_counts
    })

# Tag a photo 
@app.route('/photo/<int:photo_id>/tag', methods=['POST'])
@login_required
@csrf_protected
def tag_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Check if user can access the room this photo belongs to
    if not can_access_room(photo.room_id):
        flash('You do not have access to this photo', 'danger')
        return redirect(url_for('join_room'))
    
    tag_name = request.form.get('tag_name')
    x = float(request.form.get('x', 0))
    y = float(request.form.get('y', 0))
    width = float(request.form.get('width', 0))
    height = float(request.form.get('height', 0))
    
    # Create coordinates JSON
    coordinates = {
        'x': x, 
        'y': y, 
        'width': width, 
        'height': height
    }
    
    # Create the photo tag
    tag = PhotoTag(
        photo_id=photo_id,
        tag_name=tag_name,
        confidence=1.0,  # Manual tags have 100% confidence
        is_manual=True,
        box_coordinates=json.dumps(coordinates)
    )
    
    try:
        db.session.add(tag)
        db.session.commit()
        
        # Check if a person album should be created
        from models import Album
        
        # Look for an existing album for this person
        album = Album.query.filter_by(
            name=tag_name,
            room_id=photo.room_id,
            is_auto_generated=True
        ).first()
        
        # Create the album if it doesn't exist
        if not album:
            album = Album(
                name=tag_name,
                room_id=photo.room_id,
                is_auto_generated=True
            )
            db.session.add(album)
            db.session.commit()
        
        # Update the photo's album if no album is set
        if not photo.album_id:
            photo.album_id = album.id
            db.session.commit()
        
        flash('Photo tagged successfully!', 'success')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error tagging photo: {str(e)}")
        flash('An error occurred while tagging the photo', 'danger')
    
    return redirect(url_for('view_photo', photo_id=photo_id))

# Remove a tag from a photo
@app.route('/photo/<int:photo_id>/tag/<int:tag_id>/remove')
@login_required
def remove_tag(photo_id, tag_id):
    photo = Photo.query.get_or_404(photo_id)
    tag = PhotoTag.query.get_or_404(tag_id)
    
    # Check if tag belongs to the photo
    if tag.photo_id != photo_id:
        flash('Invalid tag', 'danger')
        return redirect(url_for('view_photo', photo_id=photo_id))
    
    # Check if user can access the room this photo belongs to
    if not can_access_room(photo.room_id):
        flash('You do not have access to this photo', 'danger')
        return redirect(url_for('join_room'))
    
    try:
        db.session.delete(tag)
        db.session.commit()
        flash('Tag removed successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing tag: {str(e)}")
        flash('An error occurred while removing the tag', 'danger')
    
    return redirect(url_for('view_photo', photo_id=photo_id))

# Process all photos in a room with face recognition
@app.route('/room/<int:room_id>/process-all-photos')
@login_required
def process_all_photos(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check if user is the creator or an admin
    current_user = get_current_user()
    if current_user.id != room.creator_id:
        flash('You do not have permission to perform this action', 'danger')
        return redirect(url_for('room', room_id=room_id))
    
    # Get all photos in the room
    photos = Photo.query.filter_by(room_id=room_id).all()
    
    # Process each photo
    from face_recognition_utils import process_photo_face_recognition
    processed_count = 0
    
    for photo in photos:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(room_id), photo.filename)
        if os.path.exists(file_path):
            if process_photo_face_recognition(photo.id, file_path):
                processed_count += 1
    
    flash(f'Processed {processed_count} photos with face recognition', 'success')
    return redirect(url_for('room', room_id=room_id))

# API endpoint for face recognition settings
@app.route('/api/face_recognition_settings')
@login_required
def api_face_recognition_settings():
    # Get current settings
    from face_recognition_utils import get_face_settings
    settings = get_face_settings()
    
    return jsonify({
        'min_confidence': settings.min_confidence,
        'detection_algorithm': settings.detection_algorithm,
        'face_encoding_model': settings.face_encoding_model,
        'auto_categorize': settings.auto_categorize,
        'recognition_tolerance': settings.recognition_tolerance
    })