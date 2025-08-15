import os
import shutil
import tarfile
import gzip
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import sqlalchemy
from sqlmodel import Session, select
from app.config.config import settings
from app.db.database import engine
from app.models.models import Guest, Room, Booking, PredictionDataPoint, BackgroundTask, User
from app.utils.helpers import get_current_time
from loguru import logger

async def create_backup(backup_dir: Optional[str] = None) -> str:
    """Create a full system backup including database and files"""
    # Use configured backup directory if not specified
    if not backup_dir:
        backup_dir = settings.BACKUP_DIR
    
    # Ensure backup directory exists
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"hotel_system_backup_{timestamp}.tar.gz"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    # Create temporary directory for backup files
    temp_dir = os.path.join(backup_dir, f"temp_backup_{timestamp}")
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Backup database
        db_backup_path = await backup_database(temp_dir)
        
        # Backup uploaded files
        files_backup_path = await backup_files(temp_dir)
        
        # Backup ML models
        ml_backup_path = await backup_ml_models(temp_dir)
        
        # Create backup manifest
        manifest = {
            "backup_date": get_current_time().isoformat(),
            "version": "1.0.0",  # Hardcoded for now
            "database": os.path.basename(db_backup_path),
            "files": os.path.basename(files_backup_path),
            "ml_models": os.path.basename(ml_backup_path)
        }
        
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Create compressed archive
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(temp_dir, arcname=os.path.basename(temp_dir))
        
        logger.info(f"Backup created successfully at {backup_path}")
        
        return backup_path
    
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

async def backup_database(backup_dir: str) -> str:
    """Backup database to CSV files"""
    db_dir = os.path.join(backup_dir, "database")
    Path(db_dir).mkdir(parents=True, exist_ok=True)
    
    # Get all model classes to backup
    models = [Guest, Room, Booking, PredictionDataPoint, BackgroundTask, User]
    
    with Session(engine) as session:
        for model in models:
            model_name = model.__name__
            file_path = os.path.join(db_dir, f"{model_name.lower()}.csv")
            
            # Get all records
            query = select(model)
            records = session.exec(query).all()
            
            if not records:
                # Create empty file if no records
                with open(file_path, "w") as f:
                    f.write("")
                continue
            
            # Get column names from first record
            first_record = records[0]
            columns = [col for col in first_record.dict().keys()]
            
            # Write to CSV
            with open(file_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for record in records:
                    # Convert record to dict and handle any non-serializable values
                    record_dict = record.dict()
                    for key, value in record_dict.items():
                        if isinstance(value, datetime):
                            record_dict[key] = value.isoformat()
                    writer.writerow(record_dict)
            
            logger.info(f"Backed up {len(records)} records from {model_name}")
    
    # Create a schema backup
    schema_path = os.path.join(db_dir, "schema.sql")
    
    # Get database schema
    metadata = sqlalchemy.MetaData()
    metadata.reflect(bind=engine)
    
    with open(schema_path, "w") as f:
        for table in metadata.sorted_tables:
            f.write(f"-- Table: {table.name}\n")
            f.write(str(sqlalchemy.schema.CreateTable(table)) + ";\n\n")
    
    logger.info(f"Database schema backed up to {schema_path}")
    return db_dir

async def backup_files(backup_dir: str) -> str:
    """Backup uploaded files"""
    files_dir = os.path.join(backup_dir, "files")
    Path(files_dir).mkdir(parents=True, exist_ok=True)
    
    # Backup OCR files
    ocr_source = settings.OCR_UPLOAD_DIR
    if os.path.exists(ocr_source):
        ocr_dest = os.path.join(files_dir, "ocr")
        if os.path.exists(ocr_source) and os.listdir(ocr_source):
            shutil.copytree(ocr_source, ocr_dest)
            logger.info(f"OCR files backed up from {ocr_source} to {ocr_dest}")
    
    # Backup any other important files
    # Add more file backups as needed
    
    return files_dir

async def backup_ml_models(backup_dir: str) -> str:
    """Backup ML models"""
    ml_dir = os.path.join(backup_dir, "ml_models")
    Path(ml_dir).mkdir(parents=True, exist_ok=True)
    
    # Backup ML model files
    ml_source = settings.ML_MODEL_DIR
    if os.path.exists(ml_source):
        ml_dest = os.path.join(ml_dir, "models")
        if os.path.exists(ml_source) and os.listdir(ml_source):
            shutil.copytree(ml_source, ml_dest)
            logger.info(f"ML models backed up from {ml_source} to {ml_dest}")
    
    return ml_dir

async def restore_backup(backup_path: str, restore_db: bool = True, restore_files: bool = True, restore_ml: bool = True) -> Dict[str, Any]:
    """Restore system from backup"""
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    # Create temporary directory for extraction
    temp_dir = os.path.join(os.path.dirname(backup_path), f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        # Extract backup archive
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(path=temp_dir)
        
        # Find the backup directory inside the temp directory
        backup_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d.startswith("temp_backup_")]
        if not backup_dirs:
            raise ValueError("Invalid backup format: backup directory not found")
        
        backup_dir = os.path.join(temp_dir, backup_dirs[0])
        
        # Read manifest
        manifest_path = os.path.join(backup_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            raise ValueError("Invalid backup format: manifest not found")
        
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        
        results = {"manifest": manifest}
        
        # Restore database if requested
        if restore_db:
            db_dir = os.path.join(backup_dir, "database")
            if os.path.exists(db_dir):
                db_result = await restore_database(db_dir)
                results["database"] = db_result
        
        # Restore files if requested
        if restore_files:
            files_dir = os.path.join(backup_dir, "files")
            if os.path.exists(files_dir):
                files_result = await restore_files(files_dir)
                results["files"] = files_result
        
        # Restore ML models if requested
        if restore_ml:
            ml_dir = os.path.join(backup_dir, "ml_models")
            if os.path.exists(ml_dir):
                ml_result = await restore_ml_models(ml_dir)
                results["ml_models"] = ml_result
        
        logger.info(f"Backup restored successfully from {backup_path}")
        return results
    
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

async def restore_database(db_dir: str) -> Dict[str, int]:
    """Restore database from CSV files"""
    if not os.path.exists(db_dir):
        raise FileNotFoundError(f"Database backup directory not found: {db_dir}")
    
    # Map of model classes
    model_map = {
        "guest": Guest,
        "room": Room,
        "booking": Booking,
        "predictiondatapoint": PredictionDataPoint,
        "backgroundtask": BackgroundTask,
        "user": User
    }
    
    results = {}
    
    with Session(engine) as session:
        # Process each CSV file
        for model_name, model_class in model_map.items():
            file_path = os.path.join(db_dir, f"{model_name}.csv")
            if not os.path.exists(file_path):
                logger.warning(f"Backup file not found for {model_name}")
                results[model_name] = 0
                continue
            
            # Check if file is empty
            if os.path.getsize(file_path) == 0:
                logger.info(f"Empty backup file for {model_name}, skipping")
                results[model_name] = 0
                continue
            
            # Clear existing data
            session.exec(f"DELETE FROM {model_name}")
            
            # Read CSV and insert records
            records = []
            with open(file_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert string dates back to datetime
                    for key, value in row.items():
                        if value and isinstance(value, str) and "T" in value and "+" in value:
                            try:
                                row[key] = datetime.fromisoformat(value)
                            except ValueError:
                                pass
                    
                    # Create model instance
                    record = model_class(**row)
                    records.append(record)
            
            # Bulk insert
            session.add_all(records)
            session.commit()
            
            results[model_name] = len(records)
            logger.info(f"Restored {len(records)} records to {model_name}")
    
    return results

async def restore_files(files_dir: str) -> Dict[str, int]:
    """Restore uploaded files"""
    if not os.path.exists(files_dir):
        raise FileNotFoundError(f"Files backup directory not found: {files_dir}")
    
    results = {}
    
    # Restore OCR files
    ocr_source = os.path.join(files_dir, "ocr")
    if os.path.exists(ocr_source):
        ocr_dest = settings.OCR_UPLOAD_DIR
        
        # Ensure destination directory exists
        Path(ocr_dest).mkdir(parents=True, exist_ok=True)
        
        # Clear existing files
        for item in os.listdir(ocr_dest):
            item_path = os.path.join(ocr_dest, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        # Copy files
        file_count = 0
        for item in os.listdir(ocr_source):
            source_path = os.path.join(ocr_source, item)
            dest_path = os.path.join(ocr_dest, item)
            
            if os.path.isfile(source_path):
                shutil.copy2(source_path, dest_path)
                file_count += 1
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
                file_count += len([f for f in os.listdir(source_path) if os.path.isfile(os.path.join(source_path, f))])
        
        results["ocr_files"] = file_count
        logger.info(f"Restored {file_count} OCR files to {ocr_dest}")
    
    # Restore any other important files
    # Add more file restorations as needed
    
    return results

async def restore_ml_models(ml_dir: str) -> Dict[str, int]:
    """Restore ML models"""
    if not os.path.exists(ml_dir):
        raise FileNotFoundError(f"ML models backup directory not found: {ml_dir}")
    
    results = {}
    
    # Restore ML model files
    ml_source = os.path.join(ml_dir, "models")
    if os.path.exists(ml_source):
        ml_dest = settings.ML_MODEL_DIR
        
        # Ensure destination directory exists
        Path(ml_dest).mkdir(parents=True, exist_ok=True)
        
        # Clear existing files
        for item in os.listdir(ml_dest):
            item_path = os.path.join(ml_dest, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        # Copy files
        file_count = 0
        for item in os.listdir(ml_source):
            source_path = os.path.join(ml_source, item)
            dest_path = os.path.join(ml_dest, item)
            
            if os.path.isfile(source_path):
                shutil.copy2(source_path, dest_path)
                file_count += 1
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
                file_count += len([f for f in os.listdir(source_path) if os.path.isfile(os.path.join(source_path, f))])
        
        results["model_files"] = file_count
        logger.info(f"Restored {file_count} ML model files to {ml_dest}")
    
    return results

async def list_backups(backup_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available backups with metadata"""
    # Use configured backup directory if not specified
    if not backup_dir:
        backup_dir = settings.BACKUP_DIR
    
    if not os.path.exists(backup_dir):
        return []
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.startswith("hotel_system_backup_") and filename.endswith(".tar.gz"):
            file_path = os.path.join(backup_dir, filename)
            file_stat = os.stat(file_path)
            
            # Extract timestamp from filename
            timestamp_str = filename.replace("hotel_system_backup_", "").replace(".tar.gz", "")
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except ValueError:
                timestamp = datetime.fromtimestamp(file_stat.st_mtime)
            
            backups.append({
                "filename": filename,
                "path": file_path,
                "size": file_stat.st_size,
                "created_at": timestamp.isoformat(),
                "age_days": (datetime.now() - timestamp).days
            })
    
    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups

async def cleanup_old_backups(max_age_days: int = 30, max_count: int = 10) -> int:
    """Clean up old backups, keeping the newest ones"""
    backups = await list_backups()
    
    # Filter backups by age
    old_backups = [b for b in backups if b["age_days"] > max_age_days]
    
    # Keep only the newest max_count backups
    if len(backups) > max_count:
        # Sort by age (oldest first)
        backups.sort(key=lambda x: x["created_at"])
        # Mark excess backups for deletion
        excess_backups = backups[:(len(backups) - max_count)]
        # Combine with old backups, avoiding duplicates
        backups_to_delete = list({b["path"]: b for b in old_backups + excess_backups}.values())
    else:
        backups_to_delete = old_backups
    
    # Delete backups
    deleted_count = 0
    for backup in backups_to_delete:
        try:
            os.unlink(backup["path"])
            deleted_count += 1
            logger.info(f"Deleted old backup: {backup['filename']}")
        except Exception as e:
            logger.error(f"Failed to delete backup {backup['filename']}: {str(e)}")
    
    return deleted_count