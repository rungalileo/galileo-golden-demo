#!/usr/bin/env python3
"""
Check Available Galileo Scorers

This script prints out all available Galileo scorers that can be used in experiments.
Run this if you get errors about missing scorer attributes.
"""
from dotenv import load_dotenv, find_dotenv
import os

# Load environment
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
load_dotenv(find_dotenv(usecwd=True), override=True)

try:
    from galileo.schema.metrics import GalileoScorers
    
    print("=" * 80)
    print("Available Galileo Scorers")
    print("=" * 80)
    print("\nAll available scorer attributes:\n")
    
    # Get all non-private attributes
    scorers = [attr for attr in dir(GalileoScorers) if not attr.startswith('_')]
    
    for i, scorer in enumerate(scorers, 1):
        print(f"{i:2}. {scorer}")
    
    print("\n" + "=" * 80)
    print(f"Total: {len(scorers)} scorers available")
    print("=" * 80)
    
    print("\n💡 Usage example:")
    print("from galileo.schema.metrics import GalileoScorers")
    print("metrics = [GalileoScorers.completeness, GalileoScorers.correctness]")
    print()
    
except ImportError as e:
    print(f"❌ Error importing GalileoScorers: {e}")
    print("\nMake sure you have the galileo package installed:")
    print("  pip install galileo")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

