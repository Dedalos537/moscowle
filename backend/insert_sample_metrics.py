#!/usr/bin/env python3
"""
Sample data insertion script for SessionMetrics table.
This script creates example session metrics for testing purposes.

Usage:
    python insert_sample_metrics.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app import create_app
from app.extensions import db
from app.models.session_metrics import SessionMetrics
from app.models.patient import Patient


def insert_sample_data():
    """Insert sample session metrics for testing."""
    app = create_app()
    
    with app.app_context():
        print("[Sample Data] Starting insertion of sample session metrics...")
        
        try:
            # Get existing patients
            patients = Patient.query.limit(5).all()
            
            if not patients:
                print("[Sample Data] ⚠️  No patients found in database. Creating test patients...")
                # Create test patients
                test_patients = [
                    Patient(first_name="Juan", last_name="Pérez"),
                    Patient(first_name="María", last_name="García"),
                    Patient(first_name="Carlos", last_name="López"),
                    Patient(first_name="Ana", last_name="Martínez"),
                    Patient(first_name="David", last_name="Rodríguez"),
                ]
                for patient in test_patients:
                    db.session.add(patient)
                db.session.commit()
                patients = test_patients
                print(f"[Sample Data] ✅ Created {len(test_patients)} test patients")
            
            # Game names for therapeutic activities
            games = [
                "Memory Match",
                "Shape Sorting",
                "Puzzle Builder",
                "Color Recognition",
                "Sound Matching",
                "Pattern Recognition"
            ]
            
            # Insert sample metrics
            sample_metrics = []
            base_date = datetime.utcnow() - timedelta(days=30)
            
            for patient in patients:
                # Create 5-8 sessions per patient
                for _ in range(random.randint(5, 8)):
                    game_name = random.choice(games)
                    
                    # Realistic performance data
                    accuracy = random.uniform(65, 98)
                    avg_time = random.uniform(1.0, 5.0)
                    failed_attempts = random.randint(0, 5)
                    current_level = random.randint(1, 3)
                    
                    # Predict next level based on accuracy
                    if accuracy >= 90:
                        next_level = current_level + 1 if current_level < 3 else 3
                    elif accuracy >= 75:
                        next_level = current_level
                    else:
                        next_level = max(1, current_level - 1)
                    
                    # Optional cluster assignment (50% chance)
                    cluster_id = random.randint(1, 3) if random.random() > 0.5 else None
                    
                    metric = SessionMetrics(
                        patient_id=patient.id,
                        game_name=game_name,
                        accuracy_rate=round(accuracy, 2),
                        average_time=round(avg_time, 2),
                        failed_attempts=failed_attempts,
                        previous_level=current_level,
                        predicted_next_level=next_level,
                        cluster_id=cluster_id,
                        created_at=base_date + timedelta(days=random.randint(0, 30))
                    )
                    
                    sample_metrics.append(metric)
                    db.session.add(metric)
            
            db.session.commit()
            
            print(f"[Sample Data] ✅ Inserted {len(sample_metrics)} sample session metrics")
            
            # Print summary
            total_metrics = SessionMetrics.query.count()
            patients_with_metrics = db.session.query(SessionMetrics.patient_id).distinct().count()
            unique_games = db.session.query(SessionMetrics.game_name).distinct().count()
            
            print(f"\n[Sample Data] Summary:")
            print(f"  - Total metrics: {total_metrics}")
            print(f"  - Patients with data: {patients_with_metrics}")
            print(f"  - Unique games: {unique_games}")
            
            # Show sample metrics
            print(f"\n[Sample Data] Sample metrics:")
            for metric in sample_metrics[:3]:
                print(f"  - {metric.patient_id}: {metric.game_name} | Accuracy: {metric.accuracy_rate}% | Level: {metric.previous_level} → {metric.predicted_next_level}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"[Sample Data] ❌ Error inserting sample data: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = insert_sample_data()
    sys.exit(0 if success else 1)
