#!/usr/bin/env python3
"""
Build Chaos Logs - Generate rich log data with chaos-induced errors

This script:
1. Fetches a dataset from Galileo API
2. Runs each input through the agent 3 times (not as experiment)
3. Creates individual traces with chaos enabled
4. Builds up error patterns for Galileo Insights to analyze

Usage:
    python build_chaos_logs.py --dataset-name my-dataset
    python build_chaos_logs.py --dataset-id abc123
    python build_chaos_logs.py --count 20  # Generate 20 queries x 3 runs = 60 traces
"""
import os
import sys
import argparse
import time
import uuid
from dotenv import load_dotenv, find_dotenv
from galileo import galileo_context
from galileo.datasets import get_dataset
from agent_factory import AgentFactory
from chaos_engine import get_chaos_engine

# Load environment
load_dotenv(os.path.expanduser("~/.config/secrets/myapps.env"), override=False)
load_dotenv(find_dotenv(usecwd=True), override=True)

# Configuration
DOMAIN = "finance"
FRAMEWORK = "LangGraph"
PROJECT_NAME = os.getenv("GALILEO_PROJECT", "finance-agent-experiments")
LOG_STREAM_NAME = "chaos-log-builder"


def setup_chaos_modes(args):
    """Configure chaos based on command line arguments"""
    chaos = get_chaos_engine()
    
    # Enable chaos modes
    if args.tool_instability:
        chaos.enable_tool_instability(True, args.tool_failure_rate)
    
    if args.sloppiness:
        chaos.enable_sloppiness(True, args.sloppiness_rate)
    
    if args.rag_chaos:
        chaos.enable_rag_chaos(True, args.rag_failure_rate)
    
    if args.rate_limit:
        chaos.enable_rate_limit_chaos(True, args.rate_limit_rate)
    
    if args.data_corruption:
        chaos.enable_data_corruption(True, args.corruption_rate)
    
    # Show what's enabled
    stats = chaos.get_stats()
    print("\n🔥 Chaos Configuration:")
    if stats['tool_instability']:
        print(f"   ✓ Tool Instability (rate: {chaos.tool_failure_rate*100}%)")
    if stats['sloppiness']:
        print(f"   ✓ Sloppiness (rate: {chaos.sloppiness_rate*100}%)")
    if stats['rag_chaos']:
        print(f"   ✓ RAG Chaos (rate: {chaos.rag_failure_rate*100}%)")
    if stats['rate_limit_chaos']:
        print(f"   ✓ Rate Limits (rate: {chaos.rate_limit_rate*100}%)")
    if stats['data_corruption']:
        print(f"   ✓ Data Corruption (rate: {chaos.data_corruption_rate*100}%)")
    
    if not any([stats['tool_instability'], stats['sloppiness'], stats['rag_chaos'], 
               stats['rate_limit_chaos'], stats['data_corruption']]):
        print("   ℹ️  No chaos enabled (use --all-chaos or individual flags)")
    
    return chaos


def fetch_dataset(dataset_name=None, dataset_id=None, inline_count=None):
    """Fetch dataset from Galileo or generate inline data"""
    
    if dataset_name:
        print(f"\n📥 Fetching dataset from Galileo: {dataset_name}")
        dataset = get_dataset(name=dataset_name)
        print(f"   ✓ Loaded dataset: {dataset_name}")
        # Convert to list of dicts
        if hasattr(dataset, 'to_dict'):
            data = dataset.to_dict('records')
        elif isinstance(dataset, list):
            data = dataset
        else:
            data = list(dataset)
        return data
    
    elif dataset_id:
        print(f"\n📥 Fetching dataset from Galileo by ID: {dataset_id}")
        dataset = get_dataset(id=dataset_id)
        print(f"   ✓ Loaded dataset ID: {dataset_id}")
        if hasattr(dataset, 'to_dict'):
            data = dataset.to_dict('records')
        elif isinstance(dataset, list):
            data = dataset
        else:
            data = list(dataset)
        return data
    
    else:
        # Generate inline test data
        count = inline_count or 10
        print(f"\n📊 Generating {count} inline test queries")
        
        test_queries = [
            "What's the current price of AAPL?",
            "What's the price of TSLA?",
            "How much is NVDA?",
            "Get me the price of GOOGL",
            "What's MSFT trading at?",
            "Buy 10 shares of NVDA",
            "Purchase 5 shares of TSLA",
            "What's the latest news on AAPL?",
            "Tell me about Tesla's recent developments",
            "What was Costco's Q3 revenue?",
            "How did Adobe perform last quarter?",
            "Buy 15 shares of AAPL",
            "What's happening in the tech sector?",
            "Sell 20 shares of GOOGL at $150",
            "What's the market sentiment on AI stocks?",
        ]
        
        # Cycle through queries if count > len(test_queries)
        data = []
        for i in range(count):
            query = test_queries[i % len(test_queries)]
            data.append({"input": query})
        
        return data


def run_query_with_logging(agent, query, session_id, run_number, total_runs):
    """
    Run a single query through the agent with Galileo logging
    
    This creates a trace in Galileo (not an experiment run)
    """
    try:
        # Start a new trace for this query
        logger = galileo_context.get_logger_instance()
        logger.start_trace(
            input=query,
            name=f"Chaos Log Builder - Run {run_number}/{total_runs}",
            metadata={
                "run_number": run_number,
                "total_runs": total_runs,
                "session_id": session_id,
                "chaos_enabled": True
            }
        )
        
        # Process query through agent
        messages = [{"role": "user", "content": query}]
        response = agent.process_query(messages)
        
        # Conclude trace
        logger.conclude(response)
        logger.flush()
        
        return response, None
        
    except Exception as e:
        # Log error
        logger = galileo_context.get_logger_instance()
        logger.conclude(f"Error: {str(e)}")
        logger.flush()
        
        return None, str(e)


def build_chaos_logs(args):
    """Main function to build chaos logs"""
    
    print("=" * 80)
    print("🔥 CHAOS LOG BUILDER")
    print("=" * 80)
    
    # Setup chaos
    chaos = setup_chaos_modes(args)
    
    # Fetch dataset
    dataset = fetch_dataset(
        dataset_name=args.dataset_name,
        dataset_id=args.dataset_id,
        inline_count=args.count
    )
    
    print(f"\n📊 Dataset Summary:")
    print(f"   Total queries: {len(dataset)}")
    print(f"   Runs per query: {args.runs}")
    print(f"   Total traces to create: {len(dataset) * args.runs}")
    
    # Initialize Galileo session
    session_id = f"chaos-{uuid.uuid4().hex[:8]}"
    print(f"\n🔧 Initializing Galileo session: {session_id}")
    
    try:
        galileo_context.start_session(
            name="Chaos Log Builder",
            external_id=session_id,
            project=PROJECT_NAME,
            log_stream=LOG_STREAM_NAME
        )
    except Exception as e:
        print(f"⚠️  Warning: Could not start Galileo session: {e}")
        print("   Continuing anyway...")
    
    # Initialize agent
    print(f"\n🤖 Initializing {FRAMEWORK} agent for domain: {DOMAIN}")
    factory = AgentFactory()
    agent = factory.create_agent(
        domain=DOMAIN,
        framework=FRAMEWORK,
        session_id=session_id
    )
    print(f"   ✓ Agent initialized with {len(agent.tools)} tools")
    
    # Process queries
    print(f"\n{'=' * 80}")
    print("PROCESSING QUERIES")
    print("=" * 80)
    
    total_queries = len(dataset) * args.runs
    current = 0
    successful = 0
    failed = 0
    chaos_triggered = 0
    
    for idx, row in enumerate(dataset, 1):
        query = row.get("input", "")
        
        print(f"\n📝 Query {idx}/{len(dataset)}: {query[:60]}...")
        
        for run in range(1, args.runs + 1):
            current += 1
            
            # Small delay between runs
            if run > 1:
                time.sleep(args.delay)
            
            print(f"   Run {run}/{args.runs}: ", end="", flush=True)
            
            # Run query
            response, error = run_query_with_logging(
                agent, query, session_id, current, total_queries
            )
            
            if error:
                print(f"❌ FAILED - {error[:50]}...")
                failed += 1
                if "CHAOS" in error or any(x in error for x in ["unavailable", "timeout", "limit"]):
                    chaos_triggered += 1
            else:
                print(f"✓ Success ({len(response)} chars)")
                successful += 1
                
                # Check if response looks like it had chaos (transposed numbers, etc.)
                if response and any(char in response for char in ["$", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
                    # Could have sloppiness - will be detected in Galileo
                    pass
        
        # Progress indicator
        progress = (current / total_queries) * 100
        print(f"   Progress: {current}/{total_queries} ({progress:.1f}%)")
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print("=" * 80)
    
    print(f"\n📊 Execution Statistics:")
    print(f"   Total traces created: {current}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Chaos events (visible): {chaos_triggered}")
    
    chaos_stats = chaos.get_stats()
    print(f"\n🔥 Chaos Statistics:")
    print(f"   API calls made: {chaos_stats['api_call_count']}")
    print(f"   Sloppy outputs: {chaos_stats['sloppy_outputs']}")
    print(f"   RAG failures: {chaos_stats['rag_failures']}")
    
    print(f"\n🔗 View in Galileo Console:")
    print(f"   Project: {PROJECT_NAME}")
    print(f"   Log Stream: {LOG_STREAM_NAME}")
    print(f"   URL: https://console.galileo.ai")
    
    print(f"\n💡 What to do next:")
    print(f"   1. Go to Galileo Console")
    print(f"   2. Navigate to project: {PROJECT_NAME}")
    print(f"   3. Find log stream: {LOG_STREAM_NAME}")
    print(f"   4. View traces (should see {current} traces)")
    print(f"   5. Wait for Insights to analyze patterns")
    print(f"   6. Check Insights tab for detected anomalies")
    
    print("\n" + "=" * 80)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Build chaos logs by running dataset queries multiple times",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use Galileo dataset
  %(prog)s --dataset-name finance-queries --runs 3
  
  # Use dataset by ID
  %(prog)s --dataset-id abc123 --runs 5
  
  # Generate inline queries
  %(prog)s --count 20 --runs 3
  
  # With all chaos enabled
  %(prog)s --count 15 --all-chaos --runs 3
  
  # Custom chaos rates
  %(prog)s --dataset-name my-data --sloppiness --sloppiness-rate 0.5 --runs 3
        """
    )
    
    # Dataset source
    dataset_group = parser.add_mutually_exclusive_group()
    dataset_group.add_argument(
        '--dataset-name',
        help='Name of Galileo dataset to use'
    )
    dataset_group.add_argument(
        '--dataset-id',
        help='ID of Galileo dataset to use'
    )
    dataset_group.add_argument(
        '--count',
        type=int,
        help='Number of inline test queries to generate (if no dataset specified)'
    )
    
    # Execution parameters
    parser.add_argument(
        '--runs',
        type=int,
        default=3,
        help='Number of times to run each query (default: 3)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between runs in seconds (default: 0.5)'
    )
    
    # Chaos modes
    parser.add_argument(
        '--all-chaos',
        action='store_true',
        help='Enable all chaos modes'
    )
    
    parser.add_argument(
        '--tool-instability',
        action='store_true',
        help='Enable tool instability (API failures)'
    )
    
    parser.add_argument(
        '--sloppiness',
        action='store_true',
        help='Enable sloppiness (number transpositions)'
    )
    
    parser.add_argument(
        '--rag-chaos',
        action='store_true',
        help='Enable RAG disconnects'
    )
    
    parser.add_argument(
        '--rate-limit',
        action='store_true',
        help='Enable rate limit errors'
    )
    
    parser.add_argument(
        '--data-corruption',
        action='store_true',
        help='Enable data corruption'
    )
    
    # Chaos rates
    parser.add_argument('--tool-failure-rate', type=float, default=0.25)
    parser.add_argument('--sloppiness-rate', type=float, default=0.30)
    parser.add_argument('--rag-failure-rate', type=float, default=0.20)
    parser.add_argument('--rate-limit-rate', type=float, default=0.15)
    parser.add_argument('--corruption-rate', type=float, default=0.20)
    
    args = parser.parse_args()
    
    # If --all-chaos, enable everything
    if args.all_chaos:
        args.tool_instability = True
        args.sloppiness = True
        args.rag_chaos = True
        args.rate_limit = True
        args.data_corruption = True
    
    # If no dataset specified and no count, use default count
    if not args.dataset_name and not args.dataset_id and not args.count:
        args.count = 10
        print("ℹ️  No dataset specified, generating 10 inline queries")
    
    return args


if __name__ == "__main__":
    args = main()
    
    try:
        build_chaos_logs(args)
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

