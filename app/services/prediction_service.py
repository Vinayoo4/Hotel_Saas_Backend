import os
import uuid
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from sqlmodel import Session, select
from app.models.models import PredictionDataPoint, BackgroundTask, Room, Booking
from app.utils.helpers import get_current_time, is_weekend
from app.config.config import settings
from loguru import logger

class PredictionService:
    def __init__(self, session=None):
        self.session = session
        self.model_dir = Path(settings.ML_MODEL_DIR)
        self.model_path = self.model_dir / "occupancy_model.joblib"
        self.scaler_path = self.model_dir / "occupancy_scaler.joblib"
        self.min_data_points = settings.ML_MIN_DATA_POINTS
        self.retrain_threshold = settings.ML_RETRAIN_THRESHOLD
        
        # Ensure model directory exists
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    async def predict_occupancy(self, days: int = 7) -> Dict[str, Any]:
        """Predict occupancy for the next N days"""
        # Get current occupancy
        current_occupied, total_rooms = await self._get_current_occupancy()
        current_occupancy_rate = current_occupied / total_rooms if total_rooms > 0 else 0
        
        # Record current data point for future training
        await self._record_data_point(current_occupancy_rate)
        
        # Generate dates for prediction
        start_date = get_current_time()
        dates = [start_date + timedelta(days=i) for i in range(1, days + 1)]
        
        # Try ML prediction first
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                predictions = await self._predict_with_ml(dates)
                logger.info(f"Made ML predictions for {len(dates)} days")
            else:
                predictions = await self._predict_with_heuristic(dates)
                logger.info(f"Made heuristic predictions for {len(dates)} days")
        except Exception as e:
            logger.error(f"ML prediction failed, falling back to heuristic: {str(e)}")
            predictions = await self._predict_with_heuristic(dates)
        
        # Calculate averages
        predicted_occupancy_rates = [p["occupancy_rate"] for p in predictions]
        avg_predicted_rate = sum(predicted_occupancy_rates) / len(predicted_occupancy_rates)
        avg_predicted_occupied = round(avg_predicted_rate * total_rooms)
        
        return {
            "current_occupied": current_occupied,
            "total_rooms": total_rooms,
            "current_occupancy_rate": f"{current_occupancy_rate:.2%}",
            "avg_predicted_occupied": avg_predicted_occupied,
            "avg_predicted_rate": f"{avg_predicted_rate:.2%}",
            "daily_predictions": predictions
        }
    
    async def _get_current_occupancy(self) -> Tuple[int, int]:
        """Get current occupancy statistics"""
        # Count total rooms
        total_rooms_query = select(Room)
        total_rooms = len(self.session.exec(total_rooms_query).all())
        
        # Count occupied rooms
        occupied_rooms_query = select(Room).where(Room.occupied == True)
        occupied_rooms = len(self.session.exec(occupied_rooms_query).all())
        
        return occupied_rooms, total_rooms
    
    async def _record_data_point(self, occupancy_rate: float) -> PredictionDataPoint:
        """Record current occupancy data point for future training"""
        current_time = get_current_time()
        
        # Calculate average stay duration
        avg_stay_duration = await self._calculate_avg_stay_duration()
        
        # Calculate average room rate
        avg_room_rate = await self._calculate_avg_room_rate()
        
        # Create data point
        data_point = PredictionDataPoint(
            date=current_time,
            day_of_week=current_time.weekday(),
            month=current_time.month,
            is_weekend=is_weekend(current_time),
            occupancy_rate=occupancy_rate,
            avg_stay_duration=avg_stay_duration,
            avg_room_rate=avg_room_rate,
            created_at=current_time
        )
        
        self.session.add(data_point)
        self.session.commit()
        self.session.refresh(data_point)
        
        logger.info(f"Recorded prediction data point: {data_point.id} with occupancy rate: {occupancy_rate:.2f}")
        return data_point
    
    async def _calculate_avg_stay_duration(self) -> float:
        """Calculate average stay duration for completed bookings"""
        # Get completed bookings from the last 30 days
        thirty_days_ago = get_current_time() - timedelta(days=30)
        query = select(Booking).where(
            Booking.checkout_at != None,
            Booking.checkin_at >= thirty_days_ago
        )
        bookings = self.session.exec(query).all()
        
        if not bookings:
            return 0.0
        
        # Calculate durations
        durations = []
        for booking in bookings:
            if booking.checkout_at and booking.checkin_at:
                duration = (booking.checkout_at - booking.checkin_at).days or 1
                durations.append(duration)
        
        return sum(durations) / len(durations) if durations else 0.0
    
    async def _calculate_avg_room_rate(self) -> float:
        """Calculate average room rate for active bookings"""
        # Get active bookings
        query = select(Booking).where(Booking.checkout_at == None)
        bookings = self.session.exec(query).all()
        
        if not bookings:
            # Fall back to room rates if no active bookings
            room_query = select(Room)
            rooms = self.session.exec(room_query).all()
            if not rooms:
                return 0.0
            return sum(room.rate_per_night for room in rooms) / len(rooms)
        
        # Calculate average rate
        rates = [booking.price for booking in bookings if booking.price is not None]
        return sum(rates) / len(rates) if rates else 0.0
    
    async def _predict_with_ml(self, dates: List[datetime]) -> List[Dict[str, Any]]:
        """Make predictions using trained ML model"""
        # Load model and scaler
        model = joblib.load(self.model_path)
        scaler = joblib.load(self.scaler_path)
        
        # Prepare features for prediction
        features = []
        for date in dates:
            features.append([
                date.weekday(),  # day_of_week
                date.month,     # month
                1 if is_weekend(date) else 0,  # is_weekend
                await self._calculate_avg_stay_duration(),  # avg_stay_duration
                await self._calculate_avg_room_rate()  # avg_room_rate
            ])
        
        # Scale features
        scaled_features = scaler.transform(features)
        
        # Make predictions
        predictions = model.predict(scaled_features)
        
        # Ensure predictions are within valid range [0, 1]
        predictions = np.clip(predictions, 0, 1)
        
        # Format results
        results = []
        for i, date in enumerate(dates):
            results.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_of_week": date.strftime("%A"),
                "is_weekend": is_weekend(date),
                "occupancy_rate": float(predictions[i]),
                "occupancy_percentage": f"{float(predictions[i]):.2%}"
            })
        
        return results
    
    async def _predict_with_heuristic(self, dates: List[datetime]) -> List[Dict[str, Any]]:
        """Make predictions using heuristic model when ML model is not available"""
        # Get historical data if available
        query = select(PredictionDataPoint)
        data_points = self.session.exec(query).all()
        
        # Calculate baseline occupancy rate
        if data_points:
            baseline_rate = sum(dp.occupancy_rate for dp in data_points) / len(data_points)
        else:
            # If no historical data, use current occupancy
            current_occupied, total_rooms = await self._get_current_occupancy()
            baseline_rate = current_occupied / total_rooms if total_rooms > 0 else 0.5
        
        # Apply heuristic rules
        results = []
        for date in dates:
            # Weekend adjustment: higher occupancy on weekends
            weekend_factor = 1.2 if is_weekend(date) else 1.0
            
            # Month adjustment: higher in peak seasons (adjust as needed)
            month_factor = 1.1 if date.month in [6, 7, 8, 12] else 1.0
            
            # Calculate predicted rate with adjustments
            predicted_rate = baseline_rate * weekend_factor * month_factor
            
            # Ensure rate is within valid range [0, 1]
            predicted_rate = min(max(predicted_rate, 0.0), 1.0)
            
            results.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_of_week": date.strftime("%A"),
                "is_weekend": is_weekend(date),
                "occupancy_rate": predicted_rate,
                "occupancy_percentage": f"{predicted_rate:.2%}"
            })
        
        return results
    
    async def get_prediction_data(self, limit: int = 100) -> List[PredictionDataPoint]:
        """Get historical prediction data points"""
        query = select(PredictionDataPoint).order_by(PredictionDataPoint.date.desc()).limit(limit)
        return self.session.exec(query).all()
    
    async def create_training_task(self) -> BackgroundTask:
        """Create a background task for model training"""
        # Check if we have enough data points
        query = select(PredictionDataPoint)
        data_points_count = len(self.session.exec(query).all())
        
        if data_points_count < self.min_data_points:
            raise ValueError(f"Not enough data points for training. Need at least {self.min_data_points}, but have {data_points_count}.")
        
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask(
            task_id=task_id,
            task_type="ml_training",
            status="pending",
            created_at=get_current_time()
        )
        
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        
        logger.info(f"Created ML training task: {task_id} with {data_points_count} data points")
        return task
    
    async def train_model(self, task_id: str) -> Dict[str, Any]:
        """Train prediction model using collected data points"""
        # Update task status
        task = self.session.get(BackgroundTask, task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        task.status = "running"
        self.session.add(task)
        self.session.commit()
        
        try:
            # Get data points
            query = select(PredictionDataPoint)
            data_points = self.session.exec(query).all()
            
            if len(data_points) < self.min_data_points:
                raise ValueError(f"Not enough data points for training. Need at least {self.min_data_points}, but have {len(data_points)}.")
            
            # Prepare data for training
            X = []
            y = []
            
            for dp in data_points:
                X.append([
                    dp.day_of_week,
                    dp.month,
                    1 if dp.is_weekend else 0,
                    dp.avg_stay_duration or 0,
                    dp.avg_room_rate or 0
                ])
                y.append(dp.occupancy_rate)
            
            X = np.array(X)
            y = np.array(y)
            
            # Split data into training and validation sets
            X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_val_scaled = scaler.transform(X_val)
            
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_val_scaled)
            mae = mean_absolute_error(y_val, y_pred)
            rmse = np.sqrt(mean_squared_error(y_val, y_pred))
            r2 = r2_score(y_val, y_pred)
            
            # Save model and scaler
            joblib.dump(model, self.model_path)
            joblib.dump(scaler, self.scaler_path)
            
            # Get feature importance
            feature_names = ['day_of_week', 'month', 'is_weekend', 'avg_stay_duration', 'avg_room_rate']
            feature_importance = {name: float(importance) for name, importance in zip(feature_names, model.feature_importances_)}
            
            # Prepare result
            result = {
                "algorithm": "RandomForestRegressor",
                "features": feature_names,
                "target": "occupancy_rate",
                "metrics": {
                    "mae": float(mae),
                    "rmse": float(rmse),
                    "r2": float(r2)
                },
                "feature_importance": feature_importance,
                "training_samples": len(X_train),
                "validation_samples": len(X_val),
                "trained_at": get_current_time().isoformat()
            }
            
            # Update task with result
            task.status = "completed"
            task.result = str(result)
            task.completed_at = get_current_time()
            self.session.add(task)
            self.session.commit()
            
            logger.info(f"ML model training completed for task: {task_id} with R² score: {r2:.4f}")
            return result
            
        except Exception as e:
            # Update task with error
            task.status = "failed"
            task.error = str(e)
            task.completed_at = get_current_time()
            self.session.add(task)
            self.session.commit()
            
            logger.error(f"ML model training failed for task: {task_id}. Error: {str(e)}")
            raise