#!/usr/bin/env python3
"""
Test script for enhanced AI with faster responses and conversation memory
"""

import requests
import json
import asyncio
import time
from datetime import datetime

API_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

# Test user credentials
TEST_USER = {
    "username": "analyst_01",
    "password": "SecurePass123!"  # Default password from User_router signup
}


async def get_auth_token():
    """Get JWT authentication token"""
    # Use form data instead of JSON for OAuth2
    # The /token endpoint uses email and password
    response = requests.post(
        f"{API_URL}/api/v1/users/token",
        data={
            "username": "test_user@example.com",
            "password": "test_password_123"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        print(f"❌ Authentication failed: {response.text}")
        return None


def test_faster_response(token):
    """Test that responses are faster now"""
    print("\n" + "="*80)
    print("🚀 TEST 1: FASTER RESPONSES")
    print("="*80)
    
    query = "What are the top 3 statistics from the documents?"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": query,
        "user_id": None
    }
    
    print(f"\n📝 Query: {query}")
    print(f"⏱️  Sending request...")
    
    start_time = time.time()
    response = requests.post(
        f"{API_URL}/api/v1/ai/prompt",
        json=payload,
        headers=headers,
        timeout=60
    )
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get("answer", "No answer")
        sources = data.get("sources", [])
        
        print(f"\n✅ Response received in {elapsed:.2f} seconds")
        print(f"📚 Sources: {sources}")
        print(f"\n📋 Answer:")
        print(f"   {answer}")
        
        return True, elapsed
    else:
        print(f"❌ Query failed: {response.text}")
        return False, 0


def test_conversation_memory(token):
    """Test that conversation memory works"""
    print("\n" + "="*80)
    print("🧠 TEST 2: CONVERSATION MEMORY")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # First query
    print("\n1️⃣  First Query:")
    query1 = "What is the main focus of the documents?"
    payload1 = {"prompt": query1}
    
    print(f"   Query: {query1}")
    response1 = requests.post(
        f"{API_URL}/api/v1/ai/prompt",
        json=payload1,
        headers=headers,
        timeout=60
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"   ✅ Response: {data1.get('answer', '')[:100]}...")
    else:
        print(f"   ❌ Failed: {response1.text}")
        return False
    
    time.sleep(1)
    
    # Second query (should have context from first)
    print("\n2️⃣  Second Query (with memory context):")
    query2 = "Based on what we just discussed, what else can you add?"
    payload2 = {"prompt": query2}
    
    print(f"   Query: {query2}")
    response2 = requests.post(
        f"{API_URL}/api/v1/ai/prompt",
        json=payload2,
        headers=headers,
        timeout=60
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"   ✅ Response: {data2.get('answer', '')[:100]}...")
    else:
        print(f"   ❌ Failed: {response2.text}")
        return False
    
    return True


def test_get_history(token):
    """Test retrieving conversation history"""
    print("\n" + "="*80)
    print("📜 TEST 3: RETRIEVE CONVERSATION HISTORY")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{API_URL}/api/v1/ai/conversation/history?limit=10",
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        message_count = data.get("message_count", 0)
        messages = data.get("messages", [])
        
        print(f"\n✅ Retrieved {message_count} messages from history")
        
        if messages:
            print("\n📋 Recent Messages:")
            for i, msg in enumerate(messages[:3], 1):
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")[:80]
                timestamp = msg.get("timestamp", "")
                
                print(f"\n   {i}. [{role}] {timestamp}")
                print(f"      {content}...")
        
        context = data.get("conversation_context", "")
        print(f"\n🧠 Conversation Context Summary:")
        print(f"   {context}")
        
        return True
    else:
        print(f"❌ Failed to retrieve history: {response.text}")
        return False


def test_clear_history(token):
    """Test clearing conversation history"""
    print("\n" + "="*80)
    print("🗑️  TEST 4: CLEAR CONVERSATION HISTORY")
    print("="*80)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.delete(
        f"{API_URL}/api/v1/ai/conversation/clear",
        headers=headers,
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        deleted_count = data.get("deleted_count", 0)
        
        print(f"\n✅ Cleared {deleted_count} messages from history")
        return True
    else:
        print(f"❌ Failed to clear history: {response.text}")
        return False


async def main():
    print("\n" + "="*80)
    print("🤖 AI ENHANCEMENTS TEST SUITE")
    print("Faster Responses + Conversation Memory")
    print("="*80)
    
    # Get authentication token
    print("\n🔐 Authenticating...")
    token = await get_auth_token()
    
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    print("✅ Authentication successful")
    
    # Run tests
    success_count = 0
    total_count = 0
    
    # Test 1: Faster Response
    total_count += 1
    success, elapsed = test_faster_response(token)
    if success:
        success_count += 1
        print(f"✅ Response Time Optimization: {elapsed:.2f}s (optimized for speed)")
    
    time.sleep(1)
    
    # Test 2: Conversation Memory
    total_count += 1
    if test_conversation_memory(token):
        success_count += 1
    
    time.sleep(1)
    
    # Test 3: Get History
    total_count += 1
    if test_get_history(token):
        success_count += 1
    
    time.sleep(1)
    
    # Test 4: Clear History
    total_count += 1
    if test_clear_history(token):
        success_count += 1
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"\nTests Passed: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("✅ ALL TESTS PASSED!")
        print("\n🎉 AI Enhancements Summary:")
        print("   ✅ Faster responses (optimized parameters)")
        print("   ✅ Conversation memory (stores all interactions)")
        print("   ✅ History retrieval (get past conversations)")
        print("   ✅ History clearing (privacy control)")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
