#!/usr/bin/env python3
"""
Complete End-to-End Workflow Example

This example demonstrates the full workflow:
1. Create a synthetic dataset using Galileo API
2. Wait for generation to complete
3. Run an experiment with the dataset
4. View results

For this to work, you need:
- Galileo API key configured
- OpenAI API key configured
- Agent domain set up with vector database
"""
import os
import time
from dotenv import load_dotenv, find_dotenv()

# Load environment variables
# 1) load global/shared first
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
# 2) then load per-app .env (if present) to override selectively
load_dotenv(find_dotenv(usecwd=True), override=True)

# NOTE: To create synthetic datasets programmatically, you should:
# 1. Use the Galileo MCP tool in your IDE (recommended)
# 2. Use the Galileo Console UI
# 3. Use the Galileo REST API directly (advanced)


def create_dataset_via_mcp_example():
    """
    Example of creating a dataset via MCP tool
    
    To use this, ask your AI assistant:
    "Create a Galileo synthetic dataset for finance queries with 20 samples"
    
    The assistant will use the mcp_evals_in_ide_server_create_galileo_dataset tool
    """
    print("📊 Creating Synthetic Dataset via MCP Tool")
    print("-" * 80)
    print("\nTo create a synthetic dataset, ask your AI assistant:")
    print("\n  'Create a Galileo synthetic dataset with these parameters:")
    print("   - name: finance-agent-eval-dataset")
    print("   - description: Synthetic queries for finance agent evaluation")
    print("   - count: 30")
    print("   - model: gpt-4o-mini")
    print("   - data_types: General Query, Off-Topic Query")
    print("   - sample_data: What was Costco's revenue in Q3?\\nHow is S&P 500 performing?'")
    print("\nThe assistant will:")
    print("  1. Create the dataset in Galileo")
    print("  2. Start synthetic data generation job")
    print("  3. Return a dataset_id")
    print("\nYou can then check status with validate_dataset tool")
    print("-" * 80)


def check_dataset_status_example(dataset_id: str):
    """
    Example of checking dataset generation status
    
    To use this, ask your AI assistant:
    "Check the status of dataset {dataset_id}"
    
    The assistant will use the mcp_evals_in_ide_server_validate_dataset tool
    """
    print(f"\n📊 Checking Dataset Status")
    print("-" * 80)
    print(f"\nTo check dataset status, ask your AI assistant:")
    print(f"\n  'Check the status of dataset {dataset_id}'")
    print("\nThe assistant will:")
    print("  1. Check generation progress")
    print("  2. Show preview of generated data")
    print("  3. Indicate if generation is complete")
    print("-" * 80)


def run_experiment_with_dataset(dataset_name: str):
    """
    Run experiment once dataset is ready
    """
    from run_experiment import run_with_synthetic_dataset
    
    print(f"\n🧪 Running Experiment with Dataset: {dataset_name}")
    print("-" * 80)
    
    results = run_with_synthetic_dataset(
        experiment_name=f"finance-agent-eval-{dataset_name}",
        dataset_name=dataset_name
    )
    
    print("\n✅ Experiment Complete!")
    print(f"📊 Results: {len(results)} rows processed")
    print("-" * 80)
    
    return results


def manual_workflow_example():
    """
    Example of manual workflow using Galileo Console
    """
    print("\n" + "=" * 80)
    print("📋 MANUAL WORKFLOW USING GALILEO CONSOLE")
    print("=" * 80)
    
    print("\n🔹 Step 1: Create Synthetic Dataset")
    print("-" * 80)
    print("1. Go to: https://console.galileo.ai/datasets")
    print("2. Click 'Create Dataset'")
    print("3. Choose 'Synthetic Data Generation'")
    print("4. Configure:")
    print("   - Name: finance-agent-eval-dataset")
    print("   - Description: Finance queries for agent evaluation")
    print("   - Model: gpt-4o-mini")
    print("   - Count: 30")
    print("   - Data Types: General Query, Off-Topic Query")
    print("   - Sample Data:")
    print("     ```")
    print("     What was Costco's revenue in Q3 2024?")
    print("     How is the S&P 500 performing?")
    print("     Should I invest in tech stocks?")
    print("     ```")
    print("5. Click 'Generate' and wait for completion")
    print("6. Note the dataset name")
    
    print("\n🔹 Step 2: Run Experiment")
    print("-" * 80)
    print("Run this command:")
    print("  python experiment_cli.py --dataset-name finance-agent-eval-dataset --experiment baseline-v1")
    
    print("\n🔹 Step 3: View Results")
    print("-" * 80)
    print("1. Go to: https://console.galileo.ai")
    print("2. Navigate to your project")
    print("3. Find your experiment: 'baseline-v1'")
    print("4. Analyze metrics and traces")
    
    print("\n" + "=" * 80)


def automated_workflow_via_mcp():
    """
    Example of automated workflow using MCP tools
    """
    print("\n" + "=" * 80)
    print("🤖 AUTOMATED WORKFLOW USING MCP TOOLS")
    print("=" * 80)
    
    print("\n🔹 Step 1: Ask AI to Create Dataset")
    print("-" * 80)
    print("Ask your AI assistant:")
    print("\n  'Create a Galileo synthetic dataset named finance-queries with 30 samples")
    print("   for testing a finance agent. Use gpt-4o-mini and include general queries")
    print("   and off-topic queries.'")
    print("\nThe AI will:")
    print("  - Use mcp_evals_in_ide_server_create_galileo_dataset")
    print("  - Return a dataset_id (e.g., 'abc-123-def')")
    
    print("\n🔹 Step 2: Check Dataset Status")
    print("-" * 80)
    print("Ask your AI assistant:")
    print("\n  'Check the status of dataset abc-123-def'")
    print("\nThe AI will:")
    print("  - Use mcp_evals_in_ide_server_validate_dataset")
    print("  - Show generation progress and preview data")
    
    print("\n🔹 Step 3: Run Experiment (Once Complete)")
    print("-" * 80)
    print("Run this command:")
    print("  python experiment_cli.py --dataset-name finance-queries --experiment baseline-v1")
    
    print("\n🔹 Step 4: Analyze Results")
    print("-" * 80)
    print("Ask your AI assistant:")
    print("\n  'Get insights for my logstream in project finance-agent-experiments'")
    print("\nThe AI will:")
    print("  - Use mcp_evals_in_ide_server_get_logstream_insights")
    print("  - Provide analysis of your experiment results")
    
    print("\n" + "=" * 80)


def quick_start_example():
    """
    Quick start with inline dataset
    """
    print("\n" + "=" * 80)
    print("⚡ QUICK START (No Dataset Creation Needed)")
    print("=" * 80)
    
    print("\nRun experiment with built-in sample data:")
    print("  python experiment_cli.py --inline --experiment quick-test")
    
    print("\nThis will:")
    print("  ✓ Use 5 built-in sample queries")
    print("  ✓ Process through your finance agent")
    print("  ✓ Evaluate with Galileo metrics")
    print("  ✓ Show results immediately")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 80)
    print("🎯 GALILEO EXPERIMENT WORKFLOW EXAMPLES")
    print("=" * 80)
    
    # Show all workflow options
    print("\nChoose a workflow:\n")
    print("1. Quick Start (recommended for first time)")
    print("2. Manual Workflow (using Galileo Console)")
    print("3. Automated Workflow (using MCP tools)")
    print("4. All Examples")
    print("5. Exit")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        quick_start_example()
    elif choice == "2":
        manual_workflow_example()
    elif choice == "3":
        automated_workflow_via_mcp()
    elif choice == "4":
        quick_start_example()
        manual_workflow_example()
        automated_workflow_via_mcp()
        create_dataset_via_mcp_example()
        check_dataset_status_example("example-dataset-id")
    elif choice == "5":
        print("\nGoodbye! 👋")
        sys.exit(0)
    else:
        print("\nInvalid choice. Showing all examples...")
        quick_start_example()
        manual_workflow_example()
        automated_workflow_via_mcp()
    
    print("\n📚 For more information, see EXPERIMENTS_README.md")
    print()


