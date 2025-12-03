"""
Test Script for K-Means Segmentation Function
Demonstrates how to test the run_k_means_segmentation() function

Author: AI Assistant
Date: December 3, 2025
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_k_means_segmentation():
    """
    Test the K-Means segmentation function
    """
    from app import create_app
    from app.extensions import db
    from app.models import SessionMetrics, Patient
    from app.services.ai_service import run_k_means_segmentation
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            print("\n" + "="*70)
            print("K-MEANS SEGMENTATION TEST")
            print("="*70 + "\n")
            
            # Check if database has data
            session_count = db.session.query(SessionMetrics).count()
            print(f"📊 Total sessions in database: {session_count}")
            
            if session_count == 0:
                print("⚠️  No session data found. Creating test data...")
                
                # Create test patients
                patient1 = Patient(id=1, name="Test Patient 1")
                patient2 = Patient(id=2, name="Test Patient 2")
                patient3 = Patient(id=3, name="Test Patient 3")
                
                db.session.add_all([patient1, patient2, patient3])
                db.session.commit()
                
                # Create test session metrics
                test_sessions = [
                    # Avanzados (High accuracy, Low time)
                    SessionMetrics(patient_id=1, game_name="Game1", accuracy_rate=95.0, average_time=10.0, failed_attempts=1, previous_level=1),
                    SessionMetrics(patient_id=1, game_name="Game2", accuracy_rate=92.0, average_time=12.0, failed_attempts=2, previous_level=1),
                    SessionMetrics(patient_id=1, game_name="Game3", accuracy_rate=98.0, average_time=8.0, failed_attempts=0, previous_level=2),
                    
                    # Intermedios (Medium accuracy, Medium time)
                    SessionMetrics(patient_id=2, game_name="Game1", accuracy_rate=65.0, average_time=35.0, failed_attempts=5, previous_level=1),
                    SessionMetrics(patient_id=2, game_name="Game2", accuracy_rate=70.0, average_time=30.0, failed_attempts=4, previous_level=1),
                    SessionMetrics(patient_id=2, game_name="Game3", accuracy_rate=62.0, average_time=40.0, failed_attempts=6, previous_level=1),
                    
                    # Necesitan Apoyo (Low accuracy, High time)
                    SessionMetrics(patient_id=3, game_name="Game1", accuracy_rate=35.0, average_time=80.0, failed_attempts=15, previous_level=1),
                    SessionMetrics(patient_id=3, game_name="Game2", accuracy_rate=40.0, average_time=75.0, failed_attempts=12, previous_level=1),
                    SessionMetrics(patient_id=3, game_name="Game3", accuracy_rate=30.0, average_time=90.0, failed_attempts=18, previous_level=1),
                ]
                
                db.session.add_all(test_sessions)
                db.session.commit()
                
                print(f"✓ Created {len(test_sessions)} test sessions\n")
            
            # Run K-Means segmentation
            print("🔄 Running K-Means segmentation...\n")
            result = run_k_means_segmentation(db, SessionMetrics, k=3)
            
            if result['success']:
                print("✅ SEGMENTATION SUCCESSFUL\n")
                
                # Print summary
                print(f"📈 Results Summary:")
                print(f"   - Total sessions processed: {result['total_sessions']}")
                print(f"   - Sessions updated: {result['updated_sessions']}")
                print(f"   - Number of clusters: {result['k_clusters']}")
                print(f"   - Inertia: {result['inertia']:.4f}")
                print(f"   - Silhouette Score: {result['silhouette_score']:.4f}\n")
                
                # Print centroids
                print("📍 Cluster Centroids:")
                for cluster_id, centroid in result['centroids'].items():
                    print(f"\n   {cluster_id} - {centroid['label']}:")
                    print(f"      Accuracy: {centroid['accuracy_rate']:.2f}%")
                    print(f"      Average Time: {centroid['average_time']:.2f}s")
                
                # Print cluster summaries
                print("\n\n📊 Cluster Summaries:")
                for cluster_id, summary in result['clusters_summary'].items():
                    print(f"\n   {cluster_id}:")
                    print(f"      Size: {summary['size']} sessions ({summary['percentage']:.1f}%)")
                    print(f"      Accuracy Rate:")
                    print(f"         Mean: {summary['accuracy_rate']['mean']:.2f}%")
                    print(f"         Std:  {summary['accuracy_rate']['std']:.2f}%")
                    print(f"         Range: {summary['accuracy_rate']['min']:.2f}% - {summary['accuracy_rate']['max']:.2f}%")
                    print(f"      Average Time:")
                    print(f"         Mean: {summary['average_time']['mean']:.2f}s")
                    print(f"         Std:  {summary['average_time']['std']:.2f}s")
                    print(f"         Range: {summary['average_time']['min']:.2f}s - {summary['average_time']['max']:.2f}s")
                
                # Verify database updates
                print("\n\n🗄️  Verifying database updates:")
                sessions_with_clusters = db.session.query(SessionMetrics).filter(
                    SessionMetrics.cluster_id.isnot(None)
                ).all()
                
                print(f"   Sessions with cluster_id: {len(sessions_with_clusters)}")
                
                for i, session in enumerate(sessions_with_clusters[:5], 1):
                    print(f"   {i}. Session ID {session.id}: Cluster {session.cluster_id}, "
                          f"Accuracy: {session.accuracy_rate:.2f}%, Time: {session.average_time:.2f}s")
                
                print("\n" + "="*70)
                print("✅ TEST COMPLETED SUCCESSFULLY")
                print("="*70 + "\n")
                
                return True
            else:
                print("❌ SEGMENTATION FAILED\n")
                print(f"Error: {result.get('error')}\n")
                print("="*70 + "\n")
                return False
    
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"   {str(e)}\n")
        import traceback
        traceback.print_exc()
        print("\n" + "="*70 + "\n")
        return False


if __name__ == '__main__':
    success = test_k_means_segmentation()
    sys.exit(0 if success else 1)
