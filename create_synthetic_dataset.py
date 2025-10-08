"""
Create Synthetic Datasets for Galileo Experiments

This script helps you create synthetic datasets using Galileo's API.
Datasets can then be used in experiments to evaluate your agent.
"""
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_finance_dataset_synthetic(
    name: str = "finance-agent-queries",
    description: str = "Synthetic dataset for finance agent testing",
    count: int = 20,
    model: str = "gpt-4o-mini",
    data_types: list = None
):
    """
    Create a synthetic dataset for finance agent testing
    
    Args:
        name: Name for the dataset
        description: Description of what the dataset contains
        count: Number of synthetic samples to generate (1-100)
        model: Model to use for generation
        data_types: Types of queries to generate
    """
    # You can use the Galileo MCP tool or SDK to create synthetic datasets
    # This is a placeholder showing the structure
    
    # Define data types if not provided
    if data_types is None:
        data_types = [
            "General Query",
            "Off-Topic Query",  # Test handling of out-of-scope questions
            "Multiple Questions in Query",  # Test multi-part question handling
        ]
    
    # Example queries to guide synthetic data generation
    sample_data = """
    What was Costco's revenue in Q3 2024?
    How is the S&P 500 performing?
    Can you analyze the latest earnings report for tech companies?
    What are the current market trends in the financial sector?
    Should I buy or sell stocks right now?
    """
    
    print(f"📊 Creating synthetic dataset: {name}")
    print(f"📝 Description: {description}")
    print(f"🔢 Count: {count}")
    print(f"🤖 Model: {model}")
    print(f"📋 Data types: {', '.join(data_types)}")
    print(f"\n💡 Use the Galileo MCP tool or Console to create this dataset:")
    print(f"\nParameters:")
    print(f"  - name: {name}")
    print(f"  - description: {description}")
    print(f"  - count: {count}")
    print(f"  - model: {model}")
    print(f"  - data_types: {data_types}")
    print(f"  - sample_data: (See example queries above)")
    print(f"\n🔗 Or create via Galileo Console: https://console.galileo.ai/datasets")
    

def create_dataset_from_csv(csv_path: str, dataset_name: str):
    """
    Create a dataset from an existing CSV file
    
    The CSV should have columns: input, output, context (optional)
    
    Args:
        csv_path: Path to the CSV file
        dataset_name: Name for the dataset in Galileo
    """
    import pandas as pd
    
    print(f"📂 Reading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    print(f"✓ Loaded {len(df)} rows")
    print(f"📋 Columns: {', '.join(df.columns.tolist())}")
    
    # Check for required columns
    if 'input' not in df.columns:
        print("⚠️  Warning: 'input' column not found. Required for experiments.")
    
    # Convert to format expected by Galileo
    dataset = df.to_dict('records')
    
    print(f"\n✓ Dataset ready with {len(dataset)} rows")
    print(f"💡 Upload to Galileo via Console or use in inline experiment")
    
    return dataset


def validate_dataset_structure(dataset: list):
    """
    Validate that a dataset has the correct structure for experiments
    
    Args:
        dataset: List of dicts representing the dataset
    """
    print("🔍 Validating dataset structure...")
    
    if not dataset:
        print("❌ Dataset is empty")
        return False
    
    required_fields = ['input']
    optional_fields = ['output', 'context', 'expected_output', 'metadata']
    
    first_row = dataset[0]
    
    # Check required fields
    for field in required_fields:
        if field not in first_row:
            print(f"❌ Missing required field: {field}")
            return False
    
    print(f"✓ Required fields present: {', '.join(required_fields)}")
    
    # Check optional fields
    present_optional = [f for f in optional_fields if f in first_row]
    if present_optional:
        print(f"✓ Optional fields present: {', '.join(present_optional)}")
    
    # Show sample row
    print(f"\n📝 Sample row:")
    for key, value in first_row.items():
        preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
        print(f"   {key}: {preview}")
    
    print(f"\n✅ Dataset structure is valid!")
    return True


if __name__ == "__main__":
    # Example: Create synthetic dataset (you'll use MCP tool or Console)
    create_finance_dataset_synthetic(
        name="finance-agent-eval-dataset",
        description="Synthetic queries for evaluating the finance agent across various scenarios",
        count=30,
        model="gpt-4o-mini",
        data_types=["General Query", "Off-Topic Query", "Multiple Questions in Query"]
    )
    
    print("\n" + "="*80)
    print("\n📋 NEXT STEPS:\n")
    print("1. Create the synthetic dataset using one of these methods:")
    print("   a) Use Galileo Console: https://console.galileo.ai/datasets")
    print("   b) Use the Galileo MCP tool in your IDE")
    print("   c) Use the Galileo Python SDK")
    print("\n2. Once created, note the dataset name or ID")
    print("\n3. Run experiments using run_experiment.py:")
    print("   python run_experiment.py")
    print("\n4. View results in Galileo Console")
    print("\n" + "="*80)

