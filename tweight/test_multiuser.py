#!/usr/bin/env python3
"""
Multi-User Test Script for UC-003

Tests that multiple users can:
1. Login independently
2. Save their own videos
3. Only see their own videos (isolation)
4. Not see other users' videos

Usage:
    python3 test_multiuser.py
    python3 test_multiuser.py --cleanup  # Delete test videos after

API: https://api.chrisbuilds64.com
Users: chris@chrisbuilds64.com, lars@chrisbuilds64.com, lily@chrisbuilds64.com
"""

import requests
import json
import sys
from typing import Dict, List

# Configuration
API_BASE = "https://api.chrisbuilds64.com"
USERS = {
    "chris": "chris@chrisbuilds64.com",
    "lars": "lars@chrisbuilds64.com",
    "lily": "lily@chrisbuilds64.com"
}

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(msg: str):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")

def print_error(msg: str):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

def print_info(msg: str):
    print(f"{Colors.OKCYAN}ℹ️  {msg}{Colors.ENDC}")

def login_user(email: str) -> Dict:
    """Login user and get JWT token."""
    print_info(f"Logging in: {email}")

    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": "dummy"}
    )

    if response.status_code != 200:
        print_error(f"Login failed for {email}: {response.text}")
        return None

    data = response.json()
    # Support both formats: Clerk (access_token) and Mock (token)
    token = data.get("access_token") or data.get("token")
    user_data = data.get("user", {})
    user_id = data.get("user_id") or user_data.get("id")

    print_success(f"Logged in: {email} (user_id: {user_id})")
    return {"email": email, "user_id": user_id, "token": token}

def save_video(user: Dict, video_url: str, video_name: str) -> bool:
    """Save a video for the user."""
    print_info(f"Saving video for {user['email']}: {video_name}")

    headers = {"Authorization": f"Bearer {user['token']}"}
    payload = {
        "url": video_url,
        "tags": [video_name, "multiuser-test"]
    }

    response = requests.post(
        f"{API_BASE}/videos",
        headers=headers,
        json=payload
    )

    if response.status_code not in [200, 201]:
        print_error(f"Save failed ({response.status_code}): {response.text}")
        return False

    print_success(f"Video saved: {video_name}")
    return True

def get_videos(user: Dict) -> List[Dict]:
    """Get all videos for the user."""
    print_info(f"Fetching videos for {user['email']}")

    headers = {"Authorization": f"Bearer {user['token']}"}

    response = requests.get(
        f"{API_BASE}/videos",
        headers=headers
    )

    if response.status_code != 200:
        print_error(f"Fetch failed: {response.text}")
        return []

    data = response.json()
    videos = data.get("videos", [])
    print_success(f"Found {len(videos)} videos for {user['email']}")
    return videos

def delete_video(user: Dict, video_id: int) -> bool:
    """Delete a video."""
    headers = {"Authorization": f"Bearer {user['token']}"}

    response = requests.delete(
        f"{API_BASE}/videos/{video_id}",
        headers=headers
    )

    return response.status_code == 200

def cleanup_test_videos(users: List[Dict]):
    """Delete all test videos created during this test."""
    print_header("CLEANUP: Deleting Test Videos")

    for user in users:
        videos = get_videos(user)
        for video in videos:
            if 'TEST_' in video.get('tags', ''):
                print_info(f"Deleting: {video.get('tags', 'unknown')} (id: {video['id']})")
                delete_video(user, video['id'])

    print_success("Cleanup complete")

def main():
    cleanup_mode = "--cleanup" in sys.argv

    if cleanup_mode:
        print_header("🧹 CLEANUP MODE")
    else:
        print_header("🧪 UC-003 MULTI-USER TEST")

    # Step 1: Login all users
    print_header("Step 1: Login All Users")
    users = []
    for name, email in USERS.items():
        user = login_user(email)
        if not user:
            print_error(f"Failed to login {email}. Aborting.")
            sys.exit(1)
        users.append(user)

    if cleanup_mode:
        cleanup_test_videos(users)
        return

    # Step 2: Save videos for each user
    print_header("Step 2: Save Test Videos for Each User")

    test_videos = {
        "chris": [
            ("https://youtube.com/watch?v=chris1", "TEST_Chris_Video_1"),
            ("https://youtube.com/watch?v=chris2", "TEST_Chris_Video_2"),
        ],
        "lars": [
            ("https://youtube.com/watch?v=lars1", "TEST_Lars_Video_1"),
            ("https://youtube.com/watch?v=lars2", "TEST_Lars_Video_2"),
        ],
        "lily": [
            ("https://youtube.com/watch?v=lily1", "TEST_Lily_Video_1"),
            ("https://youtube.com/watch?v=lily2", "TEST_Lily_Video_2"),
        ]
    }

    for user in users:
        name = user['email'].split('@')[0]
        for url, video_name in test_videos[name]:
            if not save_video(user, url, video_name):
                print_error(f"Failed to save video for {user['email']}. Continuing...")

    # Step 3: Verify isolation - Each user should only see their own videos
    print_header("Step 3: Verify User Isolation")

    all_passed = True

    for user in users:
        name = user['email'].split('@')[0]
        videos = get_videos(user)

        # Check: User should see their own videos
        expected_count = len(test_videos[name])
        # API stores tags as comma-separated string
        user_videos = [v for v in videos if f'TEST_{name.capitalize()}' in v.get('tags', '')]

        if len(user_videos) == expected_count:
            print_success(f"{user['email']}: Sees {len(user_videos)}/{expected_count} own videos ✅")
        else:
            print_error(f"{user['email']}: Expected {expected_count} videos, found {len(user_videos)} ❌")
            all_passed = False

        # Check: User should NOT see other users' videos
        other_videos = [v for v in videos if 'TEST_' in v.get('tags', '') and f'TEST_{name.capitalize()}' not in v.get('tags', '')]

        if len(other_videos) == 0:
            print_success(f"{user['email']}: Does NOT see other users' videos ✅")
        else:
            print_error(f"{user['email']}: Can see {len(other_videos)} videos from other users! ❌")
            for v in other_videos:
                print_error(f"  - {v.get('tags', 'no tags')} (id: {v['id']})")
            all_passed = False

    # Step 4: Summary
    print_header("TEST SUMMARY")

    if all_passed:
        print_success("🎉 ALL TESTS PASSED! Multi-user isolation is working correctly.")
        print_info("\nEach user can only see their own videos.")
        print_info("User data is properly isolated by user_id.")
        print_info("\n💡 Run 'python3 test_multiuser.py --cleanup' to delete test videos.")
    else:
        print_error("❌ TESTS FAILED! User isolation is broken.")
        print_error("Users can see each other's videos - CRITICAL BUG!")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
