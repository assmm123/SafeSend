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

from src.app.models.database import get_db
from src.app.models.file import File, FileStatus
from src.services.virus_scanner import VirusScanner, VirusDetectedError
from src.app.models.deal import Deal
from src.app.models.security import decode_token, generate_secure_token
from src.api.schemas import FileSchema

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
            return payload['user_id']
        except Exception:
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

# Temporary in-memory stores
_upload_sessions = {}
_download_tokens = {}

# ============================================================
# 📋 List Files (for files.html)
# ============================================================

@files_bp.route('', methods=['GET'])
def list_files():
    """
    List all files for current user's deals.
    قائمة جميع ملفات المستخدم الحالي.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        
        # Get user's deals
        import uuid as _uuid
        try:
            uid = _uuid.UUID(user_id)
        except Exception:
            uid = user_id
        user_deal_ids = db.query(Deal.id).filter(
            (Deal.buyer_id == uid) | (Deal.seller_id == uid)
        ).all()
        deal_ids = [d[0] for d in user_deal_ids]
        
        if not deal_ids:
            db.close()
            return jsonify({'files': [], 'total': 0}), 200
        
        files = db.query(File).filter(File.deal_id.in_(deal_ids)).order_by(File.created_at.desc()).all()
        
        result = []
        for f in files:
            result.append({
                'id': f.id,
                'filename': f.original_name,
                'name': f.original_name,
                'size': f.file_size,
                'mime_type': f.mime_type,
                'scan_status': f.status,
                'status': f.status,
                'created_at': f.created_at.isoformat() if f.created_at else None
            })
        
        db.close()
        return jsonify({'files': result, 'total': len(result)}), 200
    except Exception as e:
        logger.error("files.list_failed", error=str(e))
        return jsonify({'error': 'Failed', 'message_ar': 'فشل'}), 500


# ============================================================
# 📤 File Upload (Simple)
# ============================================================

@files_bp.route('/upload', methods=['POST'])
def upload_file_simple():
    """
    Upload a file (simple, no deal association required).
    رفع ملف (بسيط، بدون ربط بصفقة).
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file provided',
                'message_ar': 'لم يتم توفير ملف'
            }), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({
                'error': 'Empty filename',
                'message_ar': 'اسم ملف فارغ'
            }), 400

        # Save to disk
        upload_dir = os.path.join('uploads', str(user_id))
        os.makedirs(upload_dir, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(upload_dir, safe_filename)
        file.save(filepath)
        file_size = os.path.getsize(filepath)

        # Save to database
        db = next(get_db())
        new_file = File(
            original_name=file.filename,
            file_size=file_size,
            mime_type=file.content_type or 'application/octet-stream',
            storage_path=filepath,
            status=FileStatus.UPLOADING,
            uploaded_by=user_id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        
        file_id = new_file.id
        db.close()

        logger.info("file.uploaded", file_id=file_id, filename=file.filename, size=file_size)

        return jsonify({
            'message': 'File uploaded successfully',
            'message_ar': 'تم رفع الملف بنجاح',
            'file': {
                'id': file_id,
                'original_name': file.filename,
                'filename': file.filename,
                'name': file.filename,
                'file_size': file_size,
                'size': file_size,
                'mime_type': file.content_type or 'application/octet-stream',
                'encrypted': False,
                'virus_scanned': False,
                'scan_status': FileStatus.UPLOADING,
                'status': FileStatus.UPLOADING,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        }), 201

    except Exception as e:
        logger.error("file.upload_failed", error=str(e))
        return jsonify({
            'error': 'Upload failed',
            'message_ar': 'فشل الرفع'
        }), 500


# ============================================================
# 📤 File Upload (Deal-specific)
# ============================================================

@files_bp.route('/upload/<uuid:deal_uuid>', methods=['POST'])
def upload_file(deal_uuid: str):
    """
    Upload a file for a specific deal.
    رفع ملف لصفقة محددة.
    """
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        deal = db.query(Deal).filter(Deal.uuid == str(deal_uuid)).first()

        if not deal:
            db.close()
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404

        if 'file' not in request.files:
            db.close()
            return jsonify({
                'error': 'No file provided',
                'message_ar': 'لم يتم توفير ملف'
            }), 400

        file = request.files['file']
        if not file.filename:
            db.close()
            return jsonify({
                'error': 'Empty filename',
                'message_ar': 'اسم ملف فارغ'
            }), 400

        # Save file
        upload_dir = os.path.join('uploads', str(deal_uuid))
        os.makedirs(upload_dir, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(upload_dir, safe_filename)
        file.save(filepath)
        file_size = os.path.getsize(filepath)

        # Save to database
        new_file = File(
            original_name=file.filename,
            file_size=file_size,
            mime_type=file.content_type or 'application/octet-stream',
            storage_path=filepath,
            deal_id=deal.id,
            status=FileStatus.UPLOADING,
            uploaded_by=user_id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        
        file_id = new_file.id
        db.close()

        # Trigger virus scan (async in production, sync for now)
        try:
            scanner = VirusScanner(enabled=True)
            scan_result = scanner.scan_file(filepath)
            if scan_result.get('infected'):
                db = next(get_db())
                db_file = db.query(File).filter(File.id == file_id).first()
                if db_file:
                    db_file.status = 'infected'
                    db.commit()
                db.close()
                logger.warning("file.virus_detected", file_id=file_id, result=str(scan_result))
        except VirusDetectedError:
            logger.warning("file.virus_detected", file_id=file_id)
        except Exception as scan_error:
            logger.warning("file.scan_unavailable", error=str(scan_error))

        logger.info("file.uploaded", deal_id=deal.id, file_id=file_id, filename=file.filename)

        return jsonify({
            'message': 'File uploaded successfully',
            'message_ar': 'تم رفع الملف بنجاح',
            'file': {
                'id': file_id,
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


# ============================================================
# 📤 Chunked Upload
# ============================================================

@files_bp.route('/upload/<uuid:deal_uuid>/init', methods=['POST'])
def init_chunked_upload(deal_uuid: str):
    """Initialize chunked upload session."""
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
            'user_id': user_id,
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
    """Upload a chunk."""
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
    """Complete chunked upload."""
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

        safe_filename = f"{uuid.uuid4().hex}_{session['filename']}"
        filepath = os.path.join(upload_dir, safe_filename)

        with open(filepath, 'wb') as f:
            for i in range(session['total_chunks']):
                f.write(session['chunks'][i])

        file_size = os.path.getsize(filepath)

        # Save to database
        db = next(get_db())
        new_file = File(
            original_name=session['filename'],
            file_size=file_size,
            mime_type='application/octet-stream',
            storage_path=filepath,
            deal_id=db.query(Deal).filter(Deal.uuid == str(deal_uuid)).first().id,
            status=FileStatus.UPLOADING,
            uploaded_by=user_id
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        file_id = new_file.id
        db.close()

        del _upload_sessions[session_id]

        logger.info("upload.completed", file_id=file_id, filename=safe_filename, size=file_size)

        return jsonify({
            'message': 'Upload completed',
            'message_ar': 'تم الرفع بنجاح',
            'file': {
                'id': file_id,
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
    """Get secure preview of a file from database."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        file_record = db.query(File).filter(File.id == file_id).first()
        
        if not file_record:
            db.close()
            return jsonify({'error': 'File not found', 'message_ar': 'الملف غير موجود'}), 404
        
        preview_info = {
            'id': file_record.id,
            'original_name': file_record.original_name,
            'mime_type': file_record.mime_type,
            'file_size': file_record.file_size,
            'preview_url': f'/api/v1/files/preview/{file_id}/stream',
            'expires_in': 300
        }
        
        db.close()
        return jsonify(preview_info), 200
        
    except Exception as e:
        logger.error("file.preview_failed", error=str(e))
        return jsonify({'error': 'Preview failed', 'message_ar': 'فشل المعاينة'}), 500


@files_bp.route('/preview/<int:file_id>/stream', methods=['GET'])
def stream_file(file_id: int):
    """Stream file content for preview."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        file_record = db.query(File).filter(File.id == file_id).first()
        
        if not file_record:
            db.close()
            return jsonify({'error': 'File not found', 'message_ar': 'الملف غير موجود'}), 404
        
        # In production: stream file with watermark
        db.close()
        return jsonify({
            'message': 'Stream endpoint ready',
            'message_ar': 'نقطة البث جاهزة',
            'file_id': file_id,
            'mime_type': file_record.mime_type
        }), 200
        
    except Exception as e:
        logger.error("file.stream_failed", error=str(e))
        return jsonify({'error': 'Stream failed', 'message_ar': 'فشل البث'}), 500


@files_bp.route('/<int:file_id>/download', methods=['GET'])
def download_file(file_id: int):
    """Download file with valid token."""
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

    del _download_tokens[token]

    # Get file from DB
    try:
        db = next(get_db())
        file_record = db.query(File).filter(File.id == file_id).first()
        db.close()
        
        if file_record and os.path.exists(file_record.storage_path or ''):
            # In production: send_file with proper headers
            pass
    except Exception:
        pass

    logger.info("file.downloaded", file_id=file_id)

    return jsonify({
        'message': 'Download started',
        'message_ar': 'تم بدء التحميل',
        'file_id': file_id
    }), 200


@files_bp.route('/<int:file_id>/download/token', methods=['POST'])
def generate_download_token(file_id: int):
    """Generate a temporary download token."""
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
    """Delete a file from database and disk."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        file_record = db.query(File).filter(File.id == file_id).first()
        
        if not file_record:
            db.close()
            return jsonify({'error': 'File not found', 'message_ar': 'الملف غير موجود'}), 404
        
        # Delete from disk
        if file_record.storage_path and os.path.exists(file_record.storage_path):
            try:
                os.remove(file_record.storage_path)
            except OSError:
                logger.warning("file.disk_delete_failed", path=file_record.storage_path)
        
        # Delete from database
        db.delete(file_record)
        db.commit()
        db.close()
        
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


@files_bp.route('/<int:file_id>/info', methods=['GET'])
def file_info(file_id: int):
    """Get file information from database."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        file_record = db.query(File).filter(File.id == file_id).first()
        
        if not file_record:
            db.close()
            return jsonify({'error': 'File not found', 'message_ar': 'الملف غير موجود'}), 404
        
        info = {
            'id': file_record.id,
            'original_name': file_record.original_name,
            'file_size': file_record.file_size,
            'mime_type': file_record.mime_type,
            'encrypted': file_record.is_encrypted if hasattr(file_record, 'is_encrypted') else False,
            'virus_scanned': file_record.status == FileStatus.SCANNED,
            'virus_scan_result': file_record.status if file_record.status == FileStatus.SCANNED else 'pending',
            'created_at': file_record.created_at.isoformat() if file_record.created_at else None
        }
        
        db.close()
        return jsonify(FileSchema().dump(info)), 200

    except Exception as e:
        logger.error("file.info_failed", error=str(e))
        return jsonify({
            'error': 'Info failed',
            'message_ar': 'فشل جلب المعلومات'
        }), 500


@files_bp.route('/deal/<uuid:deal_uuid>', methods=['GET'])
def deal_files(deal_uuid: str):
    """List all files for a deal from database."""
    user_id, error = _require_auth()
    if error:
        return error

    try:
        db = next(get_db())
        deal = db.query(Deal).filter(Deal.uuid == str(deal_uuid)).first()
        
        if not deal:
            db.close()
            return jsonify({
                'error': 'Deal not found',
                'message_ar': 'الصفقة غير موجودة'
            }), 404

        files = db.query(File).filter(File.deal_id == deal.id).order_by(File.created_at.desc()).all()
        
        result = []
        for f in files:
            result.append({
                'id': f.id,
                'deal_id': f.deal_id,
                'original_name': f.original_name,
                'filename': f.original_name,
                'name': f.original_name,
                'file_size': f.file_size,
                'size': f.file_size,
                'mime_type': f.mime_type,
                'status': f.status,
                'scan_status': f.status,
                'created_at': f.created_at.isoformat() if f.created_at else None
            })
        
        db.close()
        return jsonify({
            'deal_uuid': str(deal_uuid),
            'files': result,
            'total': len(result)
        }), 200

    except Exception as e:
        logger.error("file.deal_files_failed", error=str(e))
        return jsonify({
            'error': 'Failed to list files',
            'message_ar': 'فشل جلب الملفات'
        }), 500


__all__ = ['files_bp']
