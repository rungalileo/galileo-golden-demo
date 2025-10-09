#!/usr/bin/env python3
"""
Quick Chaos Demo - Simplified script for fast demos

Runs 10 queries x 3 times with ALL chaos enabled.
Perfect for quickly generating chaos logs for Galileo Insights testing.

Usage:
    python quick_chaos_demo.py
"""
import subprocess
import sys

def main():
    print("=" * 80)
    print("🔥 QUICK CHAOS DEMO")
    print("=" * 80)
    print()
    print("This will:")
    print("  • Generate 10 test queries")
    print("  • Run each query 3 times")
    print("  • Enable ALL chaos modes")
    print("  • Create 30 traces with varied chaos-induced errors")
    print()
    print("Perfect for testing Galileo Insights!")
    print()
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    print("\n🚀 Running chaos log builder...")
    print()
    
    # Run the full script with all chaos enabled
    cmd = [
        "python", "build_chaos_logs.py",
        "--count", "10",
        "--runs", "3",
        "--all-chaos"
    ]
    
    subprocess.run(cmd)
    
    print("\n" + "=" * 80)
    print("✅ DONE!")
    print("=" * 80)
    print()
    print("📋 Next steps:")
    print("  1. Go to https://console.galileo.ai")
    print("  2. Navigate to your project")
    print("  3. Find log stream: 'chaos-log-builder'")
    print("  4. View 30 traces with various chaos-induced issues")
    print("  5. Wait for Insights to analyze")
    print("  6. Check Insights tab for detected patterns!")
    print()


if __name__ == "__main__":
    main()

