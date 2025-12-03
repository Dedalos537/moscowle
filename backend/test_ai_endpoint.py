#!/usr/bin/env python
"""
Test AI Recommendation Endpoint
Tests for POST /api/ai/recommend_level endpoint

Usage:
    python test_ai_endpoint.py

Author: AI Assistant
Date: December 3, 2025
"""

import sys
import os
import json
import requests

# Configuration
BASE_URL = "http://localhost:5001"
AUTH_ENDPOINT = f"{BASE_URL}/api/auth/login"
AI_ENDPOINT = f"{BASE_URL}/api/ai/recommend_level"
AI_STATUS_ENDPOINT = f"{BASE_URL}/api/ai/status"

# Test credentials (from project documentation)
TEST_EMAIL = "mamiebamos2@gmail.com"
TEST_PASSWORD = "Moscowle123!"


def get_jwt_token():
    """Get JWT token by logging in"""
    print("\n" + "="*70)
    print("1️⃣ Getting JWT Token")
    print("="*70 + "\n")
    
    login_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    print(f"Logging in as: {TEST_EMAIL}")
    response = requests.post(AUTH_ENDPOINT, json=login_data)
    
    if response.status_code == 200:
        result = response.json()
        token = result.get('access_token')
        print(f"✅ Login successful!")
        print(f"   Token: {token[:50]}...")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def get_ai_status(token):
    """Check AI service status"""
    print("\n" + "="*70)
    print("2️⃣ Checking AI Service Status")
    print("="*70 + "\n")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(AI_STATUS_ENDPOINT, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Service Status: {result.get('status')}")
        print(f"   Model Loaded: {result.get('model_loaded')}")
        print(f"   Message: {result.get('message')}")
        return True
    else:
        print(f"❌ Status check failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_recommend_level(token, metrics):
    """Test recommendation endpoint"""
    print(f"\n📊 Testing Recommendation for: {metrics.get('game_name')}")
    print("-" * 70)
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    response = requests.post(AI_ENDPOINT, json=metrics, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code in [201, 200]:
        result = response.json()
        print(f"✅ Success!")
        print(f"   Recommended Level: {result.get('recommended_level')} ({result.get('message')})")
        print(f"   Confidence: {result.get('confidence', 'N/A')}")
        if result.get('confidence'):
            probs = result.get('probabilities', {})
            print(f"   Probabilities:")
            print(f"      - Mantener:  {probs.get('Mantener', 0):.4f}")
            print(f"      - Avanzar:   {probs.get('Avanzar', 0):.4f}")
            print(f"      - Retroceder: {probs.get('Retroceder', 0):.4f}")
        print(f"   Student Message: {result.get('student_message')}")
        print(f"   Metric ID: {result.get('session_metric_id')}")
        return True
    else:
        print(f"❌ Failed!")
        print(f"   Response: {response.text}")
        return False


def main():
    """Run all tests"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*15 + "AI RECOMMENDATION ENDPOINT TEST" + " "*22 + "║")
    print("╚" + "="*68 + "╝")
    
    # Get JWT token
    token = get_jwt_token()
    if not token:
        print("\n❌ Cannot proceed without JWT token")
        return 1
    
    # Check AI service status
    if not get_ai_status(token):
        print("\n⚠️  Warning: AI service status check failed")
    
    # Test cases
    print("\n" + "="*70)
    print("3️⃣ Running Test Cases")
    print("="*70)
    
    test_cases = [
        {
            'name': 'Excellent Student (Should Advance)',
            'metrics': {
                'patient_id': 1,
                'game_name': 'Memoria Visual',
                'accuracy_rate': 95.0,
                'average_time': 30.0,
                'failed_attempts': 2,
                'previous_level': 1
            }
        },
        {
            'name': 'Good Student (Should Advance)',
            'metrics': {
                'patient_id': 1,
                'game_name': 'Atención y Concentración',
                'accuracy_rate': 85.5,
                'average_time': 45.3,
                'failed_attempts': 5,
                'previous_level': 2
            }
        },
        {
            'name': 'Average Student (Should Maintain)',
            'metrics': {
                'patient_id': 1,
                'game_name': 'Velocidad de Reacción',
                'accuracy_rate': 65.0,
                'average_time': 60.0,
                'failed_attempts': 15,
                'previous_level': 2
            }
        },
        {
            'name': 'Struggling Student (Should Regress)',
            'metrics': {
                'patient_id': 1,
                'game_name': 'Memoria Visual',
                'accuracy_rate': 35.0,
                'average_time': 100.0,
                'failed_attempts': 40,
                'previous_level': 3
            }
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}/4: {test_case['name']}")
        if test_recommend_level(token, test_case['metrics']):
            passed += 1
        else:
            failed += 1
    
    # Test error cases
    print("\n" + "="*70)
    print("4️⃣ Testing Error Cases")
    print("="*70)
    
    error_cases = [
        {
            'name': 'Missing Required Field',
            'metrics': {'patient_id': 1, 'game_name': 'Test'}  # Missing required fields
        },
        {
            'name': 'Invalid Accuracy (>100)',
            'metrics': {
                'patient_id': 1,
                'game_name': 'Test',
                'accuracy_rate': 150.0,
                'average_time': 45.3,
                'failed_attempts': 5,
                'previous_level': 2
            }
        },
        {
            'name': 'Invalid Level',
            'metrics': {
                'patient_id': 1,
                'game_name': 'Test',
                'accuracy_rate': 85.0,
                'average_time': 45.3,
                'failed_attempts': 5,
                'previous_level': 5  # Invalid: must be 1-3
            }
        },
    ]
    
    for i, error_case in enumerate(error_cases, 1):
        print(f"\nError Test {i}/3: {error_case['name']}")
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        response = requests.post(AI_ENDPOINT, json=error_case['metrics'], headers=headers)
        
        if response.status_code == 400:
            print(f"✅ Error caught correctly (400)")
            print(f"   Response: {response.json().get('message', 'No message')}")
            passed += 1
        else:
            print(f"❌ Expected 400 error, got {response.status_code}")
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    print("\n⚠️  NOTE: Make sure the backend is running!")
    print("   Command: docker compose -f docker-compose.dev.yml up --build\n")
    
    try:
        exit_code = main()
        print("\n" + "="*70 + "\n")
        sys.exit(exit_code)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend at", BASE_URL)
        print("   Make sure the backend is running:")
        print("   $ docker compose -f docker-compose.dev.yml up --build\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        sys.exit(1)
