"""
Create a custom LLM as a Judge metric using AWS Bedrock & Galileo for evaluating response quality.
"""

from pathlib import Path
import toml
from galileo.metrics import create_custom_llm_metric, OutputTypeEnum, StepType
from setup_env import setup_environment

def get_bedrock_judge_model_id() -> str:
    """Get the Bedrock judge model ID from secrets.toml.
    """
    secrets = toml.load(Path(".streamlit/secrets.toml"))
    # Try to get model alias first, fallback to raw model ID
    judge_model = secrets.get("BEDROCK_JUDGE_MODEL_ALIAS", "") or secrets.get("BEDROCK_JUDGE_MODEL_ID", "")
    if not judge_model:
        raise ValueError("BEDROCK_JUDGE_MODEL_ID or BEDROCK_JUDGE_MODEL_ALIAS not found in secrets.toml")
    return judge_model

def main():
    """Create a custom metric using AWS Bedrock."""
    judge_model = get_bedrock_judge_model_id()
    print(f"Using Bedrock model: {judge_model}\n")
    
    custom_metric = create_custom_llm_metric(
        name="Custom Metric - Response Quality",
        user_prompt="""
        You are an impartial evaluator, ensuring that LLM responses follow the given instructions.

        For this evaluation, check if the LLM response:
        1. Addresses the user's request appropriately
        2. Follows the instructions provided in the prompt
        3. Provides a relevant and helpful response

        Task: Determine if the provided LLM output follows the instructions and is helpful.
        Return true if the response follows instructions and is helpful
        Return false if the response does not follow instructions or is not helpful
        """,
        node_level=StepType.llm,
        cot_enabled=True,
        model_name=judge_model, 
        num_judges=1,
        description="Determines if the LLM response follows instructions and provides a helpful answer.",
        tags=["quality", "instructions", "demo"],
        output_type=OutputTypeEnum.BOOLEAN,
    )
    print(f"✓ Custom metric created successfully")
    return custom_metric

if __name__ == "__main__":
    setup_environment()
    main()

