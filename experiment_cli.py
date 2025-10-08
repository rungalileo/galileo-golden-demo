#!/usr/bin/env python3
"""
Galileo Experiment CLI - Easy command-line interface for running experiments

Usage:
    python experiment_cli.py --dataset-name my-dataset --experiment my-experiment-v1
    python experiment_cli.py --dataset-id abc123 --experiment my-experiment-v2
    python experiment_cli.py --inline --experiment quick-test
"""
import argparse
import sys
import os
from run_experiment import (
    run_galileo_experiment,
    run_with_synthetic_dataset,
    run_with_custom_dataset
)


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Run Galileo experiments with your agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with dataset from Galileo by name
  %(prog)s --dataset-name finance-queries --experiment baseline-v1
  
  # Run with dataset from Galileo by ID
  %(prog)s --dataset-id abc-123-def --experiment baseline-v1
  
  # Run with inline test data
  %(prog)s --inline --experiment quick-test
  
  # Specify custom project
  %(prog)s --dataset-name finance-queries --experiment baseline-v1 --project my-project
        """
    )
    
    # Dataset source (mutually exclusive)
    dataset_group = parser.add_mutually_exclusive_group(required=True)
    dataset_group.add_argument(
        '--dataset-name',
        help='Name of dataset in Galileo to use'
    )
    dataset_group.add_argument(
        '--dataset-id',
        help='ID of dataset in Galileo to use'
    )
    dataset_group.add_argument(
        '--inline',
        action='store_true',
        help='Use inline sample dataset for quick testing'
    )
    
    # Experiment configuration
    parser.add_argument(
        '--experiment',
        required=True,
        help='Name for the experiment'
    )
    
    parser.add_argument(
        '--project',
        help='Galileo project name (defaults to environment variable)',
        default=os.getenv('GALILEO_PROJECT', 'finance-agent-experiments')
    )
    
    parser.add_argument(
        '--domain',
        help='Domain to use (default: finance)',
        default='finance'
    )
    
    parser.add_argument(
        '--framework',
        help='Agent framework to use (default: LangGraph)',
        default='LangGraph'
    )
    
    return parser.parse_args()


def get_sample_dataset():
    """Get a sample inline dataset for quick testing"""
    return [
        {
            "input": "What was Costco's revenue for Q3 2024?",
            "output": "Costco reported net sales of $62.15 billion for the third quarter of fiscal 2024.",
            "context": "Financial data from Costco's 10-Q filing"
        },
        {
            "input": "How is the S&P 500 performing this year?",
            "output": "Based on the latest market data, the S&P 500 has shown strong performance in 2024.",
            "context": "S&P 500 market analysis and trends"
        },
        {
            "input": "Should I invest in technology stocks right now?",
            "output": "I can provide information about technology sector trends and performance, but I cannot give personalized investment advice. Please consult with a financial advisor for investment decisions.",
            "context": "General market information and ethical boundaries"
        },
        {
            "input": "What are the latest trends in AI adoption for financial services?",
            "output": "AI adoption in financial services is accelerating, with key trends including automated trading, fraud detection, customer service chatbots, and predictive analytics for risk assessment.",
            "context": "Industry analysis of AI in finance sector"
        },
        {
            "input": "Can you explain what a 10-Q filing is?",
            "output": "A 10-Q is a quarterly report that publicly traded companies must file with the SEC. It includes unaudited financial statements and provides a continuing view of the company's financial position during the year.",
            "context": "SEC filing requirements and definitions"
        }
    ]


def main():
    """Main CLI entry point"""
    args = parse_args()
    
    print("=" * 80)
    print("🧪 Galileo Experiment CLI")
    print("=" * 80)
    print(f"\n📊 Experiment: {args.experiment}")
    print(f"📁 Project: {args.project}")
    print(f"🏢 Domain: {args.domain}")
    print(f"🤖 Framework: {args.framework}")
    
    # Update global config (this is a bit hacky but works for the CLI)
    import run_experiment
    run_experiment.DOMAIN = args.domain
    run_experiment.FRAMEWORK = args.framework
    run_experiment.PROJECT_NAME = args.project
    
    try:
        # Run experiment based on dataset source
        if args.dataset_name:
            print(f"📥 Dataset: {args.dataset_name} (from Galileo)\n")
            results = run_with_synthetic_dataset(
                experiment_name=args.experiment,
                dataset_name=args.dataset_name
            )
        
        elif args.dataset_id:
            print(f"📥 Dataset ID: {args.dataset_id} (from Galileo)\n")
            results = run_galileo_experiment(
                experiment_name=args.experiment,
                dataset_id=args.dataset_id
            )
        
        else:  # inline
            print(f"📥 Dataset: Inline sample data ({len(get_sample_dataset())} rows)\n")
            results = run_with_custom_dataset(
                experiment_name=args.experiment,
                data=get_sample_dataset()
            )
        
        print("\n" + "=" * 80)
        print("✅ Experiment completed successfully!")
        print(f"📊 Processed {len(results)} rows")
        print(f"🔗 View results at: https://console.galileo.ai")
        print("=" * 80 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error running experiment: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())


