#!/usr/bin/env python3
"""
ML Models Generation Script for Hotel Management Backend
This script generates and trains the occupancy prediction models with sample data.
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def generate_sample_data(n_samples=1000):
    """Generate sample occupancy data for training"""
    print("Generating sample occupancy data...")
    
    # Generate dates for the last 2 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    dates = []
    occupancy_rates = []
    day_of_weeks = []
    months = []
    is_weekends = []
    avg_stay_durations = []
    avg_room_rates = []
    
    current_date = start_date
    while current_date <= end_date:
        # Weekend effect (higher occupancy on weekends)
        weekend_boost = 1.3 if current_date.weekday() >= 5 else 1.0
        
        # Seasonal effect (higher occupancy in summer and holidays)
        month = current_date.month
        seasonal_boost = 1.2 if month in [6, 7, 8, 12] else 1.0
        
        # Base occupancy rate with some randomness
        base_rate = 0.6
        random_factor = np.random.normal(0, 0.1)
        
        # Calculate occupancy rate
        occupancy_rate = min(0.95, max(0.1, 
            base_rate * weekend_boost * seasonal_boost + random_factor))
        
        # Generate related features
        avg_stay_duration = np.random.normal(2.5, 1.0)  # Average 2.5 days
        avg_room_rate = np.random.normal(150, 50)  # Average $150 per night
        
        dates.append(current_date)
        occupancy_rates.append(occupancy_rate)
        day_of_weeks.append(current_date.weekday())
        months.append(month)
        is_weekends.append(1 if current_date.weekday() >= 5 else 0)
        avg_stay_durations.append(max(1, avg_stay_duration))
        avg_room_rates.append(max(50, avg_room_rate))
        
        current_date += timedelta(days=1)
    
    # Create DataFrame
    data = pd.DataFrame({
        'date': dates,
        'day_of_week': day_of_weeks,
        'month': months,
        'is_weekend': is_weekends,
        'occupancy_rate': occupancy_rates,
        'avg_stay_duration': avg_stay_durations,
        'avg_room_rate': avg_room_rates
    })
    
    print(f"Generated {len(data)} sample data points")
    return data

def train_occupancy_model(data):
    """Train the occupancy prediction model"""
    print("Training occupancy prediction model...")
    
    # Prepare features
    feature_columns = ['day_of_week', 'month', 'is_weekend', 'avg_stay_duration', 'avg_room_rate']
    X = data[feature_columns]
    y = data['occupancy_rate']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Performance:")
    print(f"  Mean Absolute Error: {mae:.4f}")
    print(f"  Mean Squared Error: {mse:.4f}")
    print(f"  R² Score: {r2:.4f}")
    
    return model, scaler

def save_models(model, scaler, data, output_dir):
    """Save the trained models"""
    print("Saving models...")
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save model
    model_path = output_path / "occupancy_model.joblib"
    joblib.dump(model, model_path)
    print(f"Model saved to: {model_path}")
    
    # Save scaler
    scaler_path = output_path / "occupancy_scaler.joblib"
    joblib.dump(scaler, scaler_path)
    print(f"Scaler saved to: {scaler_path}")
    
    # Save sample data for testing
    sample_data_path = output_path / "sample_data.csv"
    data.to_csv(sample_data_path, index=False)
    print(f"Sample data saved to: {sample_data_path}")

def main():
    """Main function to generate ML models"""
    print("=" * 60)
    print("ML Models Generation for Hotel Management Backend")
    print("=" * 60)
    
    # Set output directory
    output_dir = "./ml_models"
    
    try:
        # Generate sample data
        data = generate_sample_data()
        
        # Train model
        model, scaler = train_occupancy_model(data)
        
        # Save models
        save_models(model, scaler, data, output_dir)
        
        print("\n" + "=" * 60)
        print("✅ ML Models generated successfully!")
        print("=" * 60)
        print(f"Models saved in: {os.path.abspath(output_dir)}")
        print("\nFiles created:")
        print("  - occupancy_model.joblib (trained Random Forest model)")
        print("  - occupancy_scaler.joblib (feature scaler)")
        print("  - sample_data.csv (training data)")
        
    except Exception as e:
        print(f"\n❌ Error generating ML models: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
