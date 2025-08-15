import os
import re
import uuid
import pytesseract
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from fastapi import UploadFile
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

from app.models.models import BackgroundTask
from app.utils.helpers import get_current_time, save_upload_file, generate_unique_filename
from app.config.config import settings
from loguru import logger

class OCRService:
    def __init__(self, session=None):
        self.session = session
        self.upload_dir = Path(settings.OCR_UPLOAD_DIR)
        self.tesseract_cmd = settings.TESSERACT_CMD
        self.default_lang = settings.OCR_DEFAULT_LANG
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure pytesseract
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
    
    async def save_document(self, file: UploadFile) -> Tuple[str, Path]:
        """Save uploaded document to disk"""
        # Validate file type
        valid_types = ["image/jpeg", "image/png", "image/tiff", "application/pdf"]
        if file.content_type not in valid_types:
            raise ValueError(f"Invalid file type: {file.content_type}. Supported types: {', '.join(valid_types)}")
        
        # Generate unique filename
        unique_filename = generate_unique_filename(file.filename)
        file_path = self.upload_dir / unique_filename
        
        # Save file
        await save_upload_file(file, file_path)
        logger.info(f"Saved OCR document: {file_path}")
        
        return unique_filename, file_path
    
    async def create_ocr_task(self, filename: str, lang: str = None) -> BackgroundTask:
        """Create a background task for OCR processing"""
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask(
            task_id=task_id,
            task_type="ocr",
            status="pending",
            result=f"{{\"filename\": \"{filename}\", \"lang\": \"{lang or self.default_lang}\"}}",
            created_at=get_current_time()
        )
        
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        
        logger.info(f"Created OCR task: {task_id} for file: {filename}")
        return task
    
    async def process_ocr(self, task_id: str, filename: str, lang: str = None) -> Dict[str, Any]:
        """Process OCR on document"""
        # Update task status
        task = self.session.get(BackgroundTask, task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        task.status = "running"
        self.session.add(task)
        self.session.commit()
        
        file_path = self.upload_dir / filename
        lang = lang or self.default_lang
        
        try:
            # Process image with OCR
            logger.info(f"Starting OCR processing for file: {filename} with language: {lang}")
            
            # Preprocess image
            preprocessed_image = self._preprocess_image(file_path)
            
            # Perform OCR
            ocr_result = pytesseract.image_to_data(
                preprocessed_image, 
                lang=lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and confidence
            text = self._extract_text_from_result(ocr_result)
            confidence = self._calculate_confidence(ocr_result)
            
            # Extract structured fields
            fields = self._extract_fields(text)
            
            # Prepare result
            result = {
                "text": text,
                "confidence": confidence,
                "fields": fields,
                "raw_data": {
                    "words": ocr_result["text"],
                    "confidences": ocr_result["conf"],
                    "word_boxes": [
                        (ocr_result["left"][i], ocr_result["top"][i], 
                         ocr_result["width"][i], ocr_result["height"][i])
                        for i in range(len(ocr_result["text"]))
                        if ocr_result["text"][i].strip()
                    ]
                }
            }
            
            # Update task with result
            task.status = "completed"
            task.result = str(result)
            task.completed_at = get_current_time()
            self.session.add(task)
            self.session.commit()
            
            logger.info(f"OCR processing completed for task: {task_id}")
            return result
            
        except Exception as e:
            # Update task with error
            task.status = "failed"
            task.error = str(e)
            task.completed_at = get_current_time()
            self.session.add(task)
            self.session.commit()
            
            logger.error(f"OCR processing failed for task: {task_id}. Error: {str(e)}")
            raise
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(f"{file_path}_enhanced.jpg"):
                    os.remove(f"{file_path}_enhanced.jpg")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary files: {str(e)}")
    
    def _preprocess_image(self, image_path: Path) -> np.ndarray:
        """Preprocess image for better OCR results"""
        # Read image with PIL
        img = Image.open(str(image_path))
        
        # Convert to grayscale
        gray = img.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced_img = enhancer.enhance(2.0)
        
        # Sharpen image
        enhancer = ImageEnhance.Sharpness(enhanced_img)
        enhanced_img = enhancer.enhance(2.0)
        
        # Apply threshold to get black and white image
        enhanced_array = np.array(enhanced_img)
        binary = np.where(enhanced_array > 150, 255, 0)
        
        return binary
    
    def _extract_text_from_result(self, ocr_result: Dict[str, Any]) -> str:
        """Extract text from OCR result"""
        text = ""
        for i in range(len(ocr_result["text"])):
            word = ocr_result["text"][i]
            if word.strip():
                # Add space between words
                if i > 0 and ocr_result["text"][i-1].strip() and ocr_result["line_num"][i] == ocr_result["line_num"][i-1]:
                    text += " "
                # Add newline between lines
                elif i > 0 and ocr_result["line_num"][i] != ocr_result["line_num"][i-1]:
                    text += "\n"
                text += word
        return text
    
    def _calculate_confidence(self, ocr_result: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        confidences = [conf for conf in ocr_result["conf"] if conf != -1]
        return sum(confidences) / len(confidences) if confidences else 0
    
    def _extract_fields(self, text: str) -> Dict[str, str]:
        """Extract structured fields from OCR text"""
        fields = {}
        
        # Extract name (assuming format like "Name: John Doe" or "NAME: JOHN DOE")
        name_match = re.search(r'(?:Name|NAME)\s*[:-]\s*([^\n]+)', text)
        if name_match:
            fields["name"] = name_match.group(1).strip()
        
        # Extract ID number (assuming format like "ID: 123456789" or various ID formats)
        id_patterns = [
            r'(?:ID|ID Number|ID No|ID NO)\s*[:-]\s*([A-Z0-9]+)',
            r'(?:Passport|PASSPORT)\s*[:-]\s*([A-Z0-9]+)',
            r'(?:Aadhar|AADHAR|Aadhaar|AADHAAR)\s*[:-]\s*([0-9]{12})',
            r'(?:DL|Driving License|DRIVING LICENSE)\s*[:-]\s*([A-Z0-9]+)'
        ]
        
        for pattern in id_patterns:
            id_match = re.search(pattern, text)
            if id_match:
                fields["id_number"] = id_match.group(1).strip()
                break
        
        # Extract date (assuming format like "Date: DD/MM/YYYY" or "DOB: DD-MM-YYYY")
        date_patterns = [
            r'(?:Date|DATE|DOB|Date of Birth)\s*[:-]\s*([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})',
            r'([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text)
            if date_match:
                fields["date"] = date_match.group(1).strip()
                break
        
        return fields
    
    async def process_document(self, document_path: str) -> Dict[str, Any]:
        """Process OCR on a document file"""
        try:
            # Process image with OCR
            logger.info(f"Starting OCR processing for document: {document_path}")
            
            # Preprocess image
            preprocessed_image = self._preprocess_image(Path(document_path))
            
            # Perform OCR
            ocr_result = pytesseract.image_to_data(
                preprocessed_image, 
                lang=self.default_lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text and confidence
            text = self._extract_text_from_result(ocr_result)
            confidence = self._calculate_confidence(ocr_result)
            
            # Extract structured fields
            fields = self._extract_fields(text)
            
            # Prepare result
            result = {
                "text": text,
                "confidence": confidence,
                "fields": fields,
                "raw_data": {
                    "words": ocr_result["text"],
                    "confidences": ocr_result["conf"],
                    "word_boxes": [
                        (ocr_result["left"][i], ocr_result["top"][i], 
                         ocr_result["width"][i], ocr_result["height"][i])
                        for i in range(len(ocr_result["text"]))
                        if ocr_result["text"][i].strip()
                    ]
                }
            }
            
            logger.info(f"OCR processing completed for document: {document_path}")
            return result
            
        except Exception as e:
            logger.error(f"OCR processing failed for document: {document_path}. Error: {str(e)}")
            raise