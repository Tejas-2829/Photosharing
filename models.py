from app import db
from datetime import datetime, timedelta
import secrets
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    photos = db.relationship('Photo', backref='user', lazy=True, cascade="all, delete-orphan")
    rooms_created = db.relationship('Room', backref='creator', lazy=True, cascade="all, delete-orphan")
    room_memberships = db.relationship('RoomMember', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.username}>'

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    album_id = db.Column(db.Integer, db.ForeignKey('album.id'), nullable=True)
    download_count = db.Column(db.Integer, default=0)
    
    tags = db.relationship('PhotoTag', backref='photo', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Photo {self.original_filename}>'

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_code = db.Column(db.String(20), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    face_recognition_enabled = db.Column(db.Boolean, default=True)
    
    photos = db.relationship('Photo', backref='room', lazy=True, cascade="all, delete-orphan")
    members = db.relationship('RoomMember', backref='room', lazy=True, cascade="all, delete-orphan")
    shareable_links = db.relationship('ShareableLink', backref='room', lazy=True, cascade="all, delete-orphan")
    albums = db.relationship('Album', backref='room', lazy=True, cascade="all, delete-orphan")
    analytics = db.relationship('Analytics', backref='room', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Room {self.name}>'

class RoomMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='member')  # 'member', 'admin'
    
    __table_args__ = (db.UniqueConstraint('room_id', 'user_id', name='unique_room_member'),)
    
    def __repr__(self):
        return f'<RoomMember user_id={self.user_id} room_id={self.room_id}>'

class PhotoTag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'), nullable=False)
    tag_name = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=True)
    is_manual = db.Column(db.Boolean, default=False)
    box_coordinates = db.Column(db.Text, nullable=True)  # JSON string with x, y, width, height
    
    def __repr__(self):
        return f'<PhotoTag {self.tag_name} for photo_id={self.photo_id}>'
    
    def get_coordinates(self):
        if self.box_coordinates:
            return json.loads(self.box_coordinates)
        return None

class ShareableLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    access_count = db.Column(db.Integer, default=0)
    
    def __init__(self, room_id, created_by, expires_in_days=None):
        self.room_id = room_id
        self.created_by = created_by
        self.token = secrets.token_urlsafe(32)
        
        if expires_in_days:
            self.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<ShareableLink token={self.token[:8]}... for room_id={self.room_id}>'

class Analytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # 'room_view', 'photo_download', 'link_access'
    event_data = db.Column(db.Text, nullable=True)  # JSON string with additional data
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Can be null for guest access
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Analytics {self.event_type} for room_id={self.room_id}>'

class FaceRecognitionSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    min_confidence = db.Column(db.Float, default=0.6)
    detection_algorithm = db.Column(db.String(50), default='hog')  # 'hog' or 'cnn'
    face_encoding_model = db.Column(db.String(50), default='small')  # 'small' or 'large'
    auto_categorize = db.Column(db.Boolean, default=True)
    recognition_tolerance = db.Column(db.Float, default=0.6)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FaceRecognitionSettings id={self.id}>'

class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    is_auto_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    photos = db.relationship('Photo', backref='album', lazy=True)
    
    def __repr__(self):
        return f'<Album {self.name} for room_id={self.room_id}>'
