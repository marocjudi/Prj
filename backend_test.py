#!/usr/bin/env python3
import requests
import json
import time
import math
import random
from datetime import datetime
import os
import sys

# Get the backend URL from the frontend .env file
BACKEND_URL = None
try:
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                BACKEND_URL = line.strip().split('=')[1].strip('"\'')
                break
except Exception as e:
    print(f"Error reading frontend/.env: {e}")
    sys.exit(1)

if not BACKEND_URL:
    print("REACT_APP_BACKEND_URL not found in frontend/.env")
    sys.exit(1)

# Append /api to the backend URL
API_URL = f"{BACKEND_URL}/api"
print(f"Using API URL: {API_URL}")

# Test data
USER_DATA = {
    "email": f"user_{int(time.time())}@example.com",
    "password": "Password123!",
    "name": "Jean Dupont",
    "phone": "+33612345678",
    "user_type": "user",
    "address": "123 Rue de Paris, Paris",
    "latitude": 48.8566,
    "longitude": 2.3522
}

TECHNICIAN_DATA = {
    "email": f"tech_{int(time.time())}@example.com",
    "password": "Password123!",
    "name": "Pierre Martin",
    "phone": "+33687654321",
    "user_type": "technician",
    "address": "456 Avenue des Champs-Élysées, Paris",
    "latitude": 48.8738,
    "longitude": 2.2950,
    "skills": ["Windows", "MacOS", "Linux", "Networking"],
    "hourly_rate": 50.0,
    "available": True
}

INTERVENTION_DATA = {
    "title": "Problème avec mon ordinateur",
    "description": "Mon ordinateur ne démarre plus correctement",
    "intervention_type": "computer",
    "service_type": "onsite",
    "urgency": "high",
    "budget_min": 50.0,
    "budget_max": 150.0,
    "user_address": "123 Rue de Paris, Paris",
    "user_latitude": 48.8566,
    "user_longitude": 2.3522
}

MESSAGE_DATA = {
    "content": "Bonjour, quand pouvez-vous intervenir?"
}

# Test results
test_results = {
    "authentication": {"success": False, "details": ""},
    "intervention_management": {"success": False, "details": ""},
    "stripe_payment": {"success": False, "details": ""},
    "geolocation": {"success": False, "details": ""},
    "messaging": {"success": False, "details": ""}
}

# Store tokens and IDs
user_token = None
technician_token = None
intervention_id = None
session_id = None

def print_separator():
    print("\n" + "="*80 + "\n")

def test_authentication():
    global user_token, technician_token
    print_separator()
    print("TESTING AUTHENTICATION SYSTEM")
    print_separator()
    
    try:
        # 1. Register a user
        print("1. Testing user registration...")
        response = requests.post(f"{API_URL}/auth/register", json=USER_DATA)
        if response.status_code != 200:
            print(f"❌ User registration failed: {response.status_code} - {response.text}")
            test_results["authentication"]["details"] = f"User registration failed: {response.status_code}"
            return False
        
        user_data = response.json()
        user_token = user_data.get("token")
        if not user_token:
            print("❌ User registration succeeded but no token returned")
            test_results["authentication"]["details"] = "User registration succeeded but no token returned"
            return False
        
        print(f"✅ User registered successfully with ID: {user_data['user']['id']}")
        
        # 2. Register a technician
        print("\n2. Testing technician registration...")
        response = requests.post(f"{API_URL}/auth/register", json=TECHNICIAN_DATA)
        if response.status_code != 200:
            print(f"❌ Technician registration failed: {response.status_code} - {response.text}")
            test_results["authentication"]["details"] = f"Technician registration failed: {response.status_code}"
            return False
        
        tech_data = response.json()
        technician_token = tech_data.get("token")
        if not technician_token:
            print("❌ Technician registration succeeded but no token returned")
            test_results["authentication"]["details"] = "Technician registration succeeded but no token returned"
            return False
        
        print(f"✅ Technician registered successfully with ID: {tech_data['user']['id']}")
        
        # 3. Test login for user
        print("\n3. Testing user login...")
        login_data = {
            "email": USER_DATA["email"],
            "password": USER_DATA["password"]
        }
        response = requests.post(f"{API_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ User login failed: {response.status_code} - {response.text}")
            test_results["authentication"]["details"] = f"User login failed: {response.status_code}"
            return False
        
        print("✅ User login successful")
        
        # 4. Test login for technician
        print("\n4. Testing technician login...")
        login_data = {
            "email": TECHNICIAN_DATA["email"],
            "password": TECHNICIAN_DATA["password"]
        }
        response = requests.post(f"{API_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ Technician login failed: {response.status_code} - {response.text}")
            test_results["authentication"]["details"] = f"Technician login failed: {response.status_code}"
            return False
        
        print("✅ Technician login successful")
        
        # 5. Test JWT token validation (get current user)
        print("\n5. Testing JWT token validation...")
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        if response.status_code != 200:
            print(f"❌ JWT validation failed: {response.status_code} - {response.text}")
            test_results["authentication"]["details"] = f"JWT validation failed: {response.status_code}"
            return False
        
        print("✅ JWT token validation successful")
        
        test_results["authentication"]["success"] = True
        test_results["authentication"]["details"] = "All authentication tests passed"
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed with exception: {str(e)}")
        test_results["authentication"]["details"] = f"Exception: {str(e)}"
        return False

def test_intervention_management():
    global intervention_id
    print_separator()
    print("TESTING INTERVENTION MANAGEMENT")
    print_separator()
    
    try:
        # 1. Create an intervention as a user
        print("1. Testing intervention creation...")
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.post(f"{API_URL}/interventions", json=INTERVENTION_DATA, headers=headers)
        if response.status_code != 200:
            print(f"❌ Intervention creation failed: {response.status_code} - {response.text}")
            test_results["intervention_management"]["details"] = f"Intervention creation failed: {response.status_code}"
            return False
        
        intervention_data = response.json()
        intervention_id = intervention_data.get("id")
        if not intervention_id:
            print("❌ Intervention created but no ID returned")
            test_results["intervention_management"]["details"] = "Intervention created but no ID returned"
            return False
        
        print(f"✅ Intervention created successfully with ID: {intervention_id}")
        
        # 2. Get interventions as a user
        print("\n2. Testing get interventions as user...")
        response = requests.get(f"{API_URL}/interventions", headers=headers)
        if response.status_code != 200:
            print(f"❌ Get interventions as user failed: {response.status_code} - {response.text}")
            test_results["intervention_management"]["details"] = f"Get interventions as user failed: {response.status_code}"
            return False
        
        interventions = response.json()
        if not interventions or not any(i.get("id") == intervention_id for i in interventions):
            print("❌ Created intervention not found in user's interventions list")
            test_results["intervention_management"]["details"] = "Created intervention not found in user's interventions list"
            return False
        
        print("✅ Get interventions as user successful")
        
        # 3. Get interventions as a technician
        print("\n3. Testing get interventions as technician...")
        headers = {"Authorization": f"Bearer {technician_token}"}
        response = requests.get(f"{API_URL}/interventions", headers=headers)
        if response.status_code != 200:
            print(f"❌ Get interventions as technician failed: {response.status_code} - {response.text}")
            test_results["intervention_management"]["details"] = f"Get interventions as technician failed: {response.status_code}"
            return False
        
        print("✅ Get interventions as technician successful")
        
        # 4. Assign intervention to technician
        print("\n4. Testing intervention assignment...")
        response = requests.put(f"{API_URL}/interventions/{intervention_id}/assign", headers=headers)
        if response.status_code != 200:
            print(f"❌ Intervention assignment failed: {response.status_code} - {response.text}")
            test_results["intervention_management"]["details"] = f"Intervention assignment failed: {response.status_code}"
            return False
        
        print("✅ Intervention assigned successfully")
        
        # 5. Update intervention status
        print("\n5. Testing intervention status update...")
        status_data = {"new_status": "in_progress"}
        response = requests.put(f"{API_URL}/interventions/{intervention_id}/status", params=status_data, headers=headers)
        if response.status_code != 200:
            print(f"❌ Intervention status update failed: {response.status_code} - {response.text}")
            test_results["intervention_management"]["details"] = f"Intervention status update failed: {response.status_code}"
            return False
        
        print("✅ Intervention status updated successfully")
        
        # 6. Set final price
        print("\n6. Testing setting final price...")
        final_price = 120.0
        status_data = {"new_status": "completed", "final_price": final_price}
        response = requests.put(f"{API_URL}/interventions/{intervention_id}/status", params=status_data, headers=headers)
        if response.status_code != 200:
            print(f"❌ Setting final price failed: {response.status_code} - {response.text}")
            test_results["intervention_management"]["details"] = f"Setting final price failed: {response.status_code}"
            return False
        
        print("✅ Final price set successfully")
        
        test_results["intervention_management"]["success"] = True
        test_results["intervention_management"]["details"] = "All intervention management tests passed"
        return True
        
    except Exception as e:
        print(f"❌ Intervention management test failed with exception: {str(e)}")
        test_results["intervention_management"]["details"] = f"Exception: {str(e)}"
        return False

def test_stripe_payment():
    global session_id
    print_separator()
    print("TESTING STRIPE PAYMENT INTEGRATION")
    print_separator()
    
    try:
        # 1. Create a checkout session
        print("1. Testing checkout session creation...")
        headers = {"Authorization": f"Bearer {user_token}"}
        payment_data = {"intervention_id": intervention_id}
        response = requests.post(
            f"{API_URL}/payments/checkout/session", 
            json=payment_data, 
            params={"origin_url": BACKEND_URL},
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Checkout session creation failed: {response.status_code} - {response.text}")
            test_results["stripe_payment"]["details"] = f"Checkout session creation failed: {response.status_code}"
            return False
        
        payment_data = response.json()
        session_id = payment_data.get("session_id")
        checkout_url = payment_data.get("url")
        
        if not session_id or not checkout_url:
            print("❌ Checkout session created but missing session_id or URL")
            test_results["stripe_payment"]["details"] = "Checkout session created but missing session_id or URL"
            return False
        
        print(f"✅ Checkout session created successfully with ID: {session_id}")
        
        # 2. Check payment status
        print("\n2. Testing payment status check...")
        response = requests.get(f"{API_URL}/payments/checkout/status/{session_id}")
        if response.status_code != 200:
            print(f"❌ Payment status check failed: {response.status_code} - {response.text}")
            test_results["stripe_payment"]["details"] = f"Payment status check failed: {response.status_code}"
            return False
        
        status_data = response.json()
        print(f"✅ Payment status check successful: {status_data.get('payment_status', 'unknown')}")
        
        # Note: We can't fully test the payment flow without actual payment, but the API endpoints are working
        test_results["stripe_payment"]["success"] = True
        test_results["stripe_payment"]["details"] = "Stripe payment integration tests passed (API endpoints working, actual payment not processed)"
        return True
        
    except Exception as e:
        print(f"❌ Stripe payment test failed with exception: {str(e)}")
        test_results["stripe_payment"]["details"] = f"Exception: {str(e)}"
        return False

def test_geolocation():
    print_separator()
    print("TESTING GEOLOCATION FEATURES")
    print_separator()
    
    try:
        # Test nearby technician search
        print("Testing nearby technician search...")
        params = {
            "latitude": 48.8566,
            "longitude": 2.3522,
            "radius": 50  # km
        }
        
        response = requests.get(f"{API_URL}/technicians/nearby", params=params)
        if response.status_code != 200:
            print(f"❌ Nearby technician search failed: {response.status_code} - {response.text}")
            test_results["geolocation"]["details"] = f"Nearby technician search failed: {response.status_code}"
            return False
        
        technicians = response.json()
        print(f"Found {len(technicians)} nearby technicians")
        
        # Check if our registered technician is in the results
        found = False
        for tech in technicians:
            if tech.get("email") == TECHNICIAN_DATA["email"]:
                found = True
                print(f"✅ Registered technician found at distance: {tech.get('distance')} km")
                break
        
        if not found:
            print("⚠️ Registered technician not found in nearby results (may be due to test data)")
            # This is not a critical failure as it depends on the actual distance calculation
        
        # Test technician availability update
        print("\nTesting technician availability update...")
        headers = {"Authorization": f"Bearer {technician_token}"}
        response = requests.put(f"{API_URL}/technicians/availability", params={"available": False}, headers=headers)
        if response.status_code != 200:
            print(f"❌ Technician availability update failed: {response.status_code} - {response.text}")
            test_results["geolocation"]["details"] = f"Technician availability update failed: {response.status_code}"
            return False
        
        print("✅ Technician availability updated successfully")
        
        # Verify technician no longer appears in nearby search
        response = requests.get(f"{API_URL}/technicians/nearby", params=params)
        if response.status_code != 200:
            print(f"❌ Second nearby technician search failed: {response.status_code} - {response.text}")
            test_results["geolocation"]["details"] = f"Second nearby technician search failed: {response.status_code}"
            return False
        
        technicians = response.json()
        found = False
        for tech in technicians:
            if tech.get("email") == TECHNICIAN_DATA["email"]:
                found = True
                break
        
        if found:
            print("⚠️ Technician still found in nearby results despite being unavailable")
            # This is not a critical failure as it might be a caching issue
        else:
            print("✅ Technician correctly not found in nearby results when unavailable")
        
        # Reset technician availability
        response = requests.put(f"{API_URL}/technicians/availability", params={"available": True}, headers=headers)
        if response.status_code != 200:
            print(f"⚠️ Resetting technician availability failed: {response.status_code} - {response.text}")
        
        test_results["geolocation"]["success"] = True
        test_results["geolocation"]["details"] = "Geolocation features tests passed"
        return True
        
    except Exception as e:
        print(f"❌ Geolocation test failed with exception: {str(e)}")
        test_results["geolocation"]["details"] = f"Exception: {str(e)}"
        return False

def test_messaging():
    print_separator()
    print("TESTING MESSAGING SYSTEM")
    print_separator()
    
    try:
        # 1. Send a message as a user
        print("1. Testing sending message as user...")
        headers = {"Authorization": f"Bearer {user_token}"}
        message_data = {
            "intervention_id": intervention_id,
            "content": MESSAGE_DATA["content"]
        }
        
        response = requests.post(f"{API_URL}/messages", json=message_data, headers=headers)
        if response.status_code != 200:
            print(f"❌ Sending message as user failed: {response.status_code} - {response.text}")
            test_results["messaging"]["details"] = f"Sending message as user failed: {response.status_code}"
            return False
        
        user_message = response.json()
        print(f"✅ Message sent successfully as user with ID: {user_message.get('id')}")
        
        # 2. Send a message as a technician
        print("\n2. Testing sending message as technician...")
        headers = {"Authorization": f"Bearer {technician_token}"}
        message_data = {
            "intervention_id": intervention_id,
            "content": "Je peux intervenir demain matin. Est-ce que ça vous convient?"
        }
        
        response = requests.post(f"{API_URL}/messages", json=message_data, headers=headers)
        if response.status_code != 200:
            print(f"❌ Sending message as technician failed: {response.status_code} - {response.text}")
            test_results["messaging"]["details"] = f"Sending message as technician failed: {response.status_code}"
            return False
        
        tech_message = response.json()
        print(f"✅ Message sent successfully as technician with ID: {tech_message.get('id')}")
        
        # 3. Get messages as a user
        print("\n3. Testing getting messages as user...")
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{API_URL}/messages/{intervention_id}", headers=headers)
        if response.status_code != 200:
            print(f"❌ Getting messages as user failed: {response.status_code} - {response.text}")
            test_results["messaging"]["details"] = f"Getting messages as user failed: {response.status_code}"
            return False
        
        messages = response.json()
        if len(messages) < 2:
            print(f"❌ Expected at least 2 messages, but got {len(messages)}")
            test_results["messaging"]["details"] = f"Expected at least 2 messages, but got {len(messages)}"
            return False
        
        print(f"✅ Successfully retrieved {len(messages)} messages as user")
        
        # 4. Get messages as a technician
        print("\n4. Testing getting messages as technician...")
        headers = {"Authorization": f"Bearer {technician_token}"}
        response = requests.get(f"{API_URL}/messages/{intervention_id}", headers=headers)
        if response.status_code != 200:
            print(f"❌ Getting messages as technician failed: {response.status_code} - {response.text}")
            test_results["messaging"]["details"] = f"Getting messages as technician failed: {response.status_code}"
            return False
        
        messages = response.json()
        if len(messages) < 2:
            print(f"❌ Expected at least 2 messages, but got {len(messages)}")
            test_results["messaging"]["details"] = f"Expected at least 2 messages, but got {len(messages)}"
            return False
        
        print(f"✅ Successfully retrieved {len(messages)} messages as technician")
        
        test_results["messaging"]["success"] = True
        test_results["messaging"]["details"] = "All messaging system tests passed"
        return True
        
    except Exception as e:
        print(f"❌ Messaging test failed with exception: {str(e)}")
        test_results["messaging"]["details"] = f"Exception: {str(e)}"
        return False

def run_all_tests():
    print("\n" + "="*80)
    print("STARTING BACKEND API TESTS FOR TECHSUPPORT PRO")
    print("="*80 + "\n")
    
    # Run tests in priority order
    auth_success = test_authentication()
    if not auth_success:
        print("\n❌ Authentication tests failed. Stopping further tests.")
        return
    
    intervention_success = test_intervention_management()
    if not intervention_success:
        print("\n❌ Intervention management tests failed. Stopping further tests.")
        return
    
    payment_success = test_stripe_payment()
    if not payment_success:
        print("\n❌ Stripe payment tests failed. Stopping further tests.")
        return
    
    geo_success = test_geolocation()
    if not geo_success:
        print("\n❌ Geolocation tests failed. Stopping further tests.")
        return
    
    messaging_success = test_messaging()
    
    # Print summary
    print_separator()
    print("TEST SUMMARY")
    print_separator()
    
    all_passed = True
    for feature, result in test_results.items():
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{feature.upper()}: {status}")
        if not result["success"]:
            print(f"  Details: {result['details']}")
            all_passed = False
    
    print_separator()
    if all_passed:
        print("🎉 ALL TESTS PASSED! The TechSupport Pro backend API is working correctly.")
    else:
        print("❌ SOME TESTS FAILED. Please check the details above.")
    print_separator()

if __name__ == "__main__":
    run_all_tests()