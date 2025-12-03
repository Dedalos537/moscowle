"""
Integration example: How to use SessionMetrics in the Games Module

This file shows how to integrate the SessionMetrics API with therapeutic game sessions
and ML-based level progression.
"""

# ============================================================================
# Example 1: Recording a Game Session (Frontend → Backend)
# ============================================================================

import requests
import json
from typing import Dict, Optional

class GameSessionRecorder:
    """Helper class to record game sessions to the backend."""
    
    def __init__(self, backend_url: str, jwt_token: str):
        self.backend_url = backend_url.rstrip('/')
        self.jwt_token = jwt_token
        self.headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        }
    
    def record_session(
        self,
        patient_id: int,
        game_name: str,
        accuracy_rate: float,
        average_time: float,
        failed_attempts: int,
        current_level: int,
        predicted_next_level: Optional[int] = None
    ) -> Dict:
        """
        Record a completed game session.
        
        Args:
            patient_id: ID of the patient
            game_name: Name of the game (e.g., "Memory Match")
            accuracy_rate: Percentage of correct answers (0-100)
            average_time: Average time per attempt in seconds
            failed_attempts: Total failed attempts in session
            current_level: Current difficulty level (1-3)
            predicted_next_level: Optional predicted next level (set by ML)
        
        Returns:
            API response with created metric data
        """
        payload = {
            'patient_id': patient_id,
            'game_name': game_name,
            'accuracy_rate': accuracy_rate,
            'average_time': average_time,
            'failed_attempts': failed_attempts,
            'previous_level': current_level,
            'predicted_next_level': predicted_next_level
        }
        
        try:
            response = requests.post(
                f'{self.backend_url}/api/session-metrics/',
                json=payload,
                headers=self.headers
            )
            
            if response.status_code == 201:
                print(f"✅ Session recorded successfully: {game_name}")
                return response.json()
            else:
                print(f"❌ Error recording session: {response.status_code}")
                print(response.json())
                return None
        
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            return None


# ============================================================================
# Example 2: React Component for Game Session Tracking
# ============================================================================

REACT_COMPONENT_CODE = """
import React, { useState } from 'react';

interface GameSession {
  patientId: number;
  gameName: string;
  startTime: Date;
  attempts: number;
  correctAnswers: number;
}

export function GameModule({ patientId, token, backendUrl }: Props) {
  const [session, setSession] = useState<GameSession | null>(null);
  const [currentLevel, setCurrentLevel] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  const startGame = (gameName: string) => {
    setSession({
      patientId,
      gameName,
      startTime: new Date(),
      attempts: 0,
      correctAnswers: 0
    });
  };

  const handleCorrectAnswer = () => {
    if (session) {
      setSession({
        ...session,
        correctAnswers: session.correctAnswers + 1,
        attempts: session.attempts + 1
      });
    }
  };

  const handleWrongAnswer = () => {
    if (session) {
      setSession({
        ...session,
        attempts: session.attempts + 1
      });
    }
  };

  const endGame = async () => {
    if (!session) return;

    setIsLoading(true);

    const endTime = new Date();
    const duration = (endTime.getTime() - session.startTime.getTime()) / 1000; // seconds
    const avgTime = duration / session.attempts;
    const accuracy = (session.correctAnswers / session.attempts) * 100;
    const failedAttempts = session.attempts - session.correctAnswers;

    try {
      const response = await fetch(
        `${backendUrl}/api/session-metrics/`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            patient_id: patientId,
            game_name: session.gameName,
            accuracy_rate: Math.round(accuracy * 100) / 100,
            average_time: Math.round(avgTime * 100) / 100,
            failed_attempts: failedAttempts,
            previous_level: currentLevel
          })
        }
      );

      if (response.ok) {
        const data = await response.json();
        
        // Update level if predicted_next_level exists
        if (data.predicted_next_level) {
          setCurrentLevel(data.predicted_next_level);
          console.log(`🎮 Level up! New level: ${data.predicted_next_level}`);
        }
        
        console.log('✅ Game session recorded');
      }
    } catch (error) {
      console.error('❌ Error recording session:', error);
    } finally {
      setIsLoading(false);
      setSession(null);
    }
  };

  return (
    <div className="game-container">
      {!session ? (
        <div className="game-selection">
          <button onClick={() => startGame('Memory Match')}>Memory Match</button>
          <button onClick={() => startGame('Shape Sorting')}>Shape Sorting</button>
          <button onClick={() => startGame('Puzzle Builder')}>Puzzle Builder</button>
        </div>
      ) : (
        <div className="game-playing">
          <h2>{session.gameName} - Level {currentLevel}</h2>
          <p>Correct: {session.correctAnswers} / {session.attempts}</p>
          <div className="game-buttons">
            <button onClick={handleCorrectAnswer} disabled={isLoading}>✓ Correct</button>
            <button onClick={handleWrongAnswer} disabled={isLoading}>✗ Wrong</button>
            <button onClick={endGame} disabled={isLoading}>
              {isLoading ? 'Saving...' : 'End Game'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
"""


# ============================================================================
# Example 3: Python Backend - ML Level Prediction
# ============================================================================

def predict_next_level_ml(patient_id: int, game_name: str) -> Optional[int]:
    """
    Example ML function to predict next level for a patient.
    This would integrate with your K-Means clustering model.
    
    Args:
        patient_id: ID of the patient
        game_name: Name of the game
    
    Returns:
        Predicted next level (1, 2, or 3) or None
    """
    from app.models.session_metrics import SessionMetrics
    from sqlalchemy import func
    
    # Get recent metrics for this patient and game
    recent_metrics = SessionMetrics.query.filter_by(
        patient_id=patient_id,
        game_name=game_name
    ).order_by(SessionMetrics.created_at.desc()).limit(10).all()
    
    if len(recent_metrics) < 3:
        # Not enough data
        return None
    
    # Calculate average accuracy over last 10 sessions
    avg_accuracy = sum(m.accuracy_rate for m in recent_metrics) / len(recent_metrics)
    avg_failed = sum(m.failed_attempts for m in recent_metrics) / len(recent_metrics)
    
    current_level = recent_metrics[0].previous_level
    
    # Simple heuristic (replace with actual ML model)
    if avg_accuracy >= 90 and avg_failed <= 1:
        # Consistently high performance
        return min(current_level + 1, 3)  # Advance level
    elif avg_accuracy < 70 and avg_failed > 3:
        # Struggling
        return max(current_level - 1, 1)  # Reduce level
    else:
        # Performing well
        return current_level  # Maintain level


# ============================================================================
# Example 4: Backend Route Extension for Auto-Level-Prediction
# ============================================================================

ROUTE_EXTENSION = """
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.models.session_metrics import SessionMetrics
from app.models.patient import Patient

# Add this route to session_metrics_routes.py

@session_metrics_bp.route('/<int:metric_id>/predict-level', methods=['POST'])
@jwt_required()
def predict_and_update_level(metric_id):
    '''
    Automatically predict next level using ML and update the metric.
    '''
    try:
        metric = SessionMetrics.query.get(metric_id)
        
        if not metric:
            return jsonify({'msg': 'Metric not found'}), 404
        
        # Call ML prediction function
        predicted_level = predict_next_level_ml(
            metric.patient_id,
            metric.game_name
        )
        
        if predicted_level:
            metric.predicted_next_level = predicted_level
            db.session.commit()
            
            return jsonify({
                'msg': 'Level prediction updated',
                'predicted_next_level': predicted_level,
                'current_level': metric.previous_level
            }), 200
        else:
            return jsonify({'msg': 'Not enough data for prediction'}), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': f'Error: {str(e)}'}), 500
"""


# ============================================================================
# Example 5: Analytics Dashboard Query
# ============================================================================

class GameAnalytics:
    """Helper class for game analytics queries."""
    
    @staticmethod
    def get_patient_progress(patient_id: int):
        """Get progress summary for a patient across all games."""
        from app.models.session_metrics import SessionMetrics
        from sqlalchemy import func
        
        # Group by game and get statistics
        stats = {}
        
        games = SessionMetrics.query.filter_by(patient_id=patient_id).with_entities(
            SessionMetrics.game_name
        ).distinct().all()
        
        for (game_name,) in games:
            metrics = SessionMetrics.query.filter_by(
                patient_id=patient_id,
                game_name=game_name
            ).all()
            
            if metrics:
                stats[game_name] = {
                    'sessions': len(metrics),
                    'avg_accuracy': round(
                        sum(m.accuracy_rate for m in metrics) / len(metrics), 2
                    ),
                    'best_accuracy': max(m.accuracy_rate for m in metrics),
                    'worst_accuracy': min(m.accuracy_rate for m in metrics),
                    'current_level': metrics[-1].previous_level,
                    'next_level': metrics[-1].predicted_next_level,
                    'trend': 'improving' if metrics[-1].accuracy_rate > metrics[0].accuracy_rate else 'stable'
                }
        
        return stats
    
    @staticmethod
    def get_game_difficulty_distribution():
        """See which levels patients are playing."""
        from app.models.session_metrics import SessionMetrics
        from sqlalchemy import func
        
        distribution = SessionMetrics.query.with_entities(
            SessionMetrics.game_name,
            SessionMetrics.previous_level,
            func.count(SessionMetrics.id).label('count')
        ).group_by(SessionMetrics.game_name, SessionMetrics.previous_level).all()
        
        return {
            'game': game,
            'level': level,
            'count': count
        } for game, level, count in distribution


# ============================================================================
# Example 6: Complete Game Flow (Step-by-step)
# ============================================================================

def complete_game_flow_example():
    """
    Complete example showing the entire flow from game completion to ML prediction.
    """
    import requests
    
    # Configuration
    BACKEND_URL = 'http://localhost:5001'
    JWT_TOKEN = 'your_jwt_token_here'
    PATIENT_ID = 5
    GAME_NAME = 'Memory Match'
    
    # Step 1: Initialize recorder
    recorder = GameSessionRecorder(BACKEND_URL, JWT_TOKEN)
    
    # Step 2: After game ends, collect metrics
    accuracy_rate = 87.5
    average_time = 2.3
    failed_attempts = 2
    current_level = 2
    
    # Step 3: Record session
    result = recorder.record_session(
        patient_id=PATIENT_ID,
        game_name=GAME_NAME,
        accuracy_rate=accuracy_rate,
        average_time=average_time,
        failed_attempts=failed_attempts,
        current_level=current_level
    )
    
    if result:
        metric_id = result['id']
        
        # Step 4: Predict next level (optional)
        predict_response = requests.post(
            f'{BACKEND_URL}/api/session-metrics/{metric_id}/predict-level',
            headers={
                'Authorization': f'Bearer {JWT_TOKEN}',
                'Content-Type': 'application/json'
            }
        )
        
        if predict_response.status_code == 200:
            prediction = predict_response.json()
            print(f"🎮 Next level predicted: {prediction['predicted_next_level']}")
        
        # Step 5: Get patient analytics
        analytics_response = requests.get(
            f'{BACKEND_URL}/api/session-metrics/patient/{PATIENT_ID}/summary',
            headers={'Authorization': f'Bearer {JWT_TOKEN}'}
        )
        
        if analytics_response.status_code == 200:
            summary = analytics_response.json()
            print(f"📊 Patient Summary:")
            print(f"  Total sessions: {summary['total_sessions']}")
            print(f"  Games played: {summary['games_played']}")


# ============================================================================
# Example 7: Database Queries (Direct SQLAlchemy)
# ============================================================================

def example_queries():
    """Common database queries for game analytics."""
    from app.models.session_metrics import SessionMetrics
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Query 1: Get all sessions for a patient in the last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent = SessionMetrics.query.filter(
        SessionMetrics.patient_id == 5,
        SessionMetrics.created_at >= week_ago
    ).order_by(SessionMetrics.created_at.desc()).all()
    
    # Query 2: Average accuracy by game
    game_stats = SessionMetrics.query.with_entities(
        SessionMetrics.game_name,
        func.avg(SessionMetrics.accuracy_rate).label('avg_accuracy'),
        func.count(SessionMetrics.id).label('total_sessions')
    ).group_by(SessionMetrics.game_name).all()
    
    # Query 3: Patients struggling (accuracy < 70%)
    struggling = SessionMetrics.query.filter(
        SessionMetrics.accuracy_rate < 70
    ).distinct(SessionMetrics.patient_id).all()
    
    # Query 4: Level distribution
    levels = SessionMetrics.query.with_entities(
        SessionMetrics.previous_level,
        func.count(SessionMetrics.id).label('count')
    ).group_by(SessionMetrics.previous_level).all()
    
    return {
        'recent_sessions': recent,
        'game_stats': game_stats,
        'struggling_patients': struggling,
        'level_distribution': levels
    }


if __name__ == '__main__':
    print("SessionMetrics Integration Examples")
    print("=" * 50)
    print("\n1. React Component example saved above")
    print("2. Route extension example saved above")
    print("3. Analytics class available in GameAnalytics")
    print("4. Complete flow available in complete_game_flow_example()")
    print("5. Common queries available in example_queries()")
