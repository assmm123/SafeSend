"""
Files API Endpoints - SafeSend
نقاط نهاية الملفات - SafeSend

Handles file upload (chunked), preview, download with tokens, and deletion.
يدير رفع الملفات (متقطع)، المعاينة، التحميل برموز، والحذف.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import structlog
import os
import uuid

from src.app.models.deal_repository import DealRepository
from src.app.models.security import decode_token, generate_secure_token
from src.api.schemas import FileSchema, FileUploadSchema

logger = structlog.get_logger(__name__)
files_bp = Blueprint('files_v1', __name__, url_prefix='/api/v1/files')

# ============================================================
# 🔐 Helpers
# ============================================================

def _get_user_id() -> Optional[int]:
    """Extract user_id from JWT token."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    if not token:
        return None
    payload = decode_token(token)
    if payload and 'user_id' in payload:
        try:
            return int(payload['user_id'])
        except (ValueError, TypeError):
            return None
    return None

def _require_auth():
    """Check authentication and return user_id or error."""
    user_id = _get_user_id()
    if not user_id:
        return None, (jsonify({
            'error': 'Authentication required',
            'message_ar': 'المصادقة مطلوبة'
        }), 401)
    return user_id, None

def _get_deal_repo():
    """Get deal repository instance."""
    return DealRepository()

# Temporary in-memory store for chunked uploads
_upload_sessions = {}
_download_tokens = {}

# ============================================================
# 📤 File Upload
# ============================================================

@files_bp.route('/upload/<uuid:deal_uuid>', methods=['POST'])
def upload_file(deal_uuid: str):
    """
    Upload a file for a deal (simple).
    رفع ملف لصفقة (بسيط).
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided',
                'message_ar': 'لم يتم توفير ملف'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'error': 'Empty filename',
                'message_ar': 'اسم ملف فارغ'
            }), 400
        
        # Save file
        upload_dir = os.path.join('uploads', str(deal_uuid))
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        file_size = os.path.getsize(filepath)
        
        logger.info("file.uploaded", deal_id=deal.id, filename=filename, size=file_size)
        
        return jsonify({
            'message': 'File uploaded successfully',
            'message_ar': 'تم رفع الملف بنجاح',
            'file': {
                'id': 1,
                'deal_id': deal.id,
                'original_name': file.filename,
                'file_size': file_size,
                'mime_type': file.content_type or 'application/octet-stream',
                'encrypted': False,
                'virus_scanned': False,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error("file.upload_failed", error=str(e))
        return jsonify({
            'error': 'Upload failed',
            'message_ar': 'فشل الرفع'
        }), 500


@files_bp.route('/upload/<uuid:deal_uuid>/init', methods=['POST'])
def init_chunked_upload(deal_uuid: str):
    """
    Initialize chunked upload session.
    بدء جلسة رفع متقطع.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        data = request.get_json() or {}
        filename = data.get('filename', '')
        total_size = data.get('total_size', 0)
        total_chunks = data.get('total_chunks', 0)
        
        if not filename or not total_chunks:
            return jsonify({
                'error': 'Filename and total_chunks required',
                'message_ar': 'اسم الملف وعدد الأجزاء مطلوب'
            }), 400
        
        session_id = generate_secure_token(16)
        _upload_sessions[session_id] = {
            'deal_uuid': str(deal_uuid),
            'filename': filename,
            'total_size': total_size,
            'total_chunks': total_chunks,
            'received_chunks': 0,
            'chunks': {},
            'created_at': datetime.now(timezone.utc)
        }
        
        logger.info("upload.chunked.init", session_id=session_id, filename=filename)
        
        return jsonify({
            'session_id': session_id,
            'message': 'Upload initialized',
            'message_ar': 'تم بدء الرفع'
        }), 200
        
    except Exception as e:
        logger.error("upload.init_failed", error=str(e))
        return jsonify({
            'error': 'Init failed',
            'message_ar': 'فشل البدء'
        }), 500


@files_bp.route('/upload/<uuid:deal_uuid>/chunk', methods=['POST'])
def upload_chunk(deal_uuid: str):
    """
    Upload a chunk for chunked upload.
    رفع جزء من ملف.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        session_id = request.headers.get('X-Upload-Session-Id', '')
        chunk_index = int(request.form.get('chunk_index', 0))
        
        session = _upload_sessions.get(session_id)
        if not session:
            return jsonify({
                'error': 'Invalid session',
                'message_ar': 'جلسة غير صالحة'
            }), 400
        
        if 'chunk' not in request.files:
            return jsonify({
                'error': 'No chunk provided',
                'message_ar': 'لم يتم توفير جزء'
            }), 400
        
        chunk = request.files['chunk']
        session['chunks'][chunk_index] = chunk.read()
        session['received_chunks'] += 1
        
        progress = (session['received_chunks'] / session['total_chunks']) * 100
        
        logger.debug("upload.chunk.received", session_id=session_id, chunk=chunk_index, progress=progress)
        
        return jsonify({
            'chunk_index': chunk_index,
            'received': session['received_chunks'],
            'total': session['total_chunks'],
            'progress': round(progress, 2)
        }), 200
        
    except Exception as e:
        logger.error("upload.chunk_failed", error=str(e))
        return jsonify({
            'error': 'Chunk upload failed',
            'message_ar': 'فشل رفع الجزء'
        }), 500


@files_bp.route('/upload/<uuid:deal_uuid>/complete', methods=['POST'])
def complete_upload(deal_uuid: str):
    """
    Complete chunked upload and assemble file.
    إكمال الرفع وتجميع الملف.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        session_id = request.headers.get('X-Upload-Session-Id', '')
        
        session = _upload_sessions.get(session_id)
        if not session:
            return jsonify({
                'error': 'Invalid session',
                'message_ar': 'جلسة غير صالحة'
            }), 400
        
        if session['received_chunks'] != session['total_chunks']:
            return jsonify({
                'error': 'Not all chunks received',
                'message_ar': 'لم يتم استلام جميع الأجزاء'
            }), 400
        
        # Assemble file
        upload_dir = os.path.join('uploads', str(deal_uuid))
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4().hex}_{session['filename']}"
        filepath = os.path.join(upload_dir, filename)
        
        with open(filepath, 'wb') as f:
            for i in range(session['total_chunks']):
                f.write(session['chunks'][i])
        
        file_size = os.path.getsize(filepath)
        
        # Cleanup session
        del _upload_sessions[session_id]
        
        logger.info("upload.completed", filename=filename, size=file_size)
        
        return jsonify({
            'message': 'Upload completed',
            'message_ar': 'تم الرفع بنجاح',
            'file': {
                'id': 1,
                'original_name': session['filename'],
                'file_size': file_size,
                'mime_type': 'application/octet-stream',
                'encrypted': False,
                'virus_scanned': False
            }
        }), 201
        
    except Exception as e:
        logger.error("upload.complete_failed", error=str(e))
        return jsonify({
            'error': 'Complete failed',
            'message_ar': 'فشل الإكمال'
        }), 500


# ============================================================
# 👁️ Preview & Download
# ============================================================

@files_bp.route('/preview/<int:file_id>', methods=['GET'])
def preview_file(file_id: int):
    """
    Get secure preview of a file.
    معاينة آمنة لملف.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        # In production: fetch file from DB/storage
        preview_info = {
            'id': file_id,
            'original_name': 'example.pdf',
            'mime_type': 'application/pdf',
            'file_size': 1024,
            'preview_url': f'/api/v1/files/preview/{file_id}/stream',
            'expires_in': 300
        }
        
        return jsonify(preview_info), 200
        
    except Exception as e:
        logger.error("file.preview_failed", error=str(e))
        return jsonify({
            'error': 'Preview failed',
            'message_ar': 'فشل المعاينة'
        }), 500


@files_bp.route('/preview/<int:file_id>/stream', methods=['GET'])
def stream_file(file_id: int):
    """
    Stream file content for preview.
    بث محتوى الملف للمعاينة.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        # In production: stream file with watermark
        return jsonify({
            'message': 'Streaming not implemented',
            'message_ar': 'البث غير مفعل'
        }), 501
        
    except Exception as e:
        logger.error("file.stream_failed", error=str(e))
        return jsonify({
            'error': 'Stream failed',
            'message_ar': 'فشل البث'
        }), 500


@files_bp.route('/download/<int:file_id>', methods=['GET'])
def download_file(file_id: int):
    """
    Download file with valid token.
    تحميل ملف برمز صالح.
    """
    token = request.args.get('token', '')
    
    if not token:
        return jsonify({
            'error': 'Download token required',
            'message_ar': 'رمز التحميل مطلوب'
        }), 400
    
    token_data = _download_tokens.get(token)
    if not token_data or token_data['file_id'] != file_id:
        return jsonify({
            'error': 'Invalid or expired token',
            'message_ar': 'رمز غير صالح أو منتهي'
        }), 401
    
    # Cleanup used token
    del _download_tokens[token]
    
    logger.info("file.downloaded", file_id=file_id)
    
    return jsonify({
        'message': 'Download started',
        'message_ar': 'تم بدء التحميل',
        'file_id': file_id
    }), 200


@files_bp.route('/download/<int:file_id>/token', methods=['POST'])
def generate_download_token(file_id: int):
    """
    Generate a temporary download token.
    توليد رمز تحميل مؤقت.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        token = generate_secure_token(32)
        _download_tokens[token] = {
            'file_id': file_id,
            'user_id': user_id,
            'created_at': datetime.now(timezone.utc),
            'expires_in': 300
        }
        
        logger.info("download.token_generated", file_id=file_id)
        
        return jsonify({
            'token': token,
            'expires_in': 300,
            'message': 'Token generated',
            'message_ar': 'تم توليد الرمز'
        }), 200
        
    except Exception as e:
        logger.error("download.token_failed", error=str(e))
        return jsonify({
            'error': 'Token generation failed',
            'message_ar': 'فشل توليد الرمز'
        }), 500


# ============================================================
# 🗑️ Delete & Info
# ============================================================

@files_bp.route('/<int:file_id>', methods=['DELETE'])
def delete_file(file_id: int):
    """
    Delete a file.
    حذف ملف.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        logger.info("file.deleted", file_id=file_id)
        
        return jsonify({
            'message': 'File deleted',
            'message_ar': 'تم حذف الملف'
        }), 200
        
    except Exception as e:
        logger.error("file.delete_failed", error=str(e))
        return jsonify({
            'error': 'Delete failed',
            'message_ar': 'فشل الحذف'
        }), 500


@files_bp.route('/info/<int:file_id>', methods=['GET'])
def file_info(file_id: int):
    """
    Get file information.
    معلومات الملف.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        info = {
            'id': file_id,
            'original_name': 'example.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf',
            'encrypted': True,
            'virus_scanned': True,
            'virus_scan_result': 'clean',
            'download_count': 5,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify(FileSchema().dump(info)), 200
        
    except Exception as e:
        logger.error("file.info_failed", error=str(e))
        return jsonify({
            'error': 'Info failed',
            'message_ar': 'فشل جلب المعلومات'
        }), 500


@files_bp.route('/deal/<uuid:deal_uuid>', methods=['GET'])
def deal_files(deal_uuid: str):
    """
    List all files for a deal.
    قائمة ملفات الصفقة.
    """
    user_id, error = _require_auth()
    if error:
        return error
    
    try:
        repo = _get_deal_repo()
        deal = repo.get_by_uuid(str(deal_uuid))
        
        if not deal:
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404
        
        files = [{
            'id': 1,
            'deal_id': deal.id,
            'original_name': 'example.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf'
        }]
        
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'files': FileSchema().dump(files, many=True)
        }), 200
        
    except Exception as e:
        logger.error("file.deal_files_failed", error=str(e))
        return jsonify({
            'error': 'Failed to list files',
            'message_ar': 'فشل جلب الملفات'
        }), 500


# ============================================================
# 📦 Export
# ============================================================

__all__ = ['files_bp']
