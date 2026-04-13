"""
Galileo Protect Helper Functions
Handles Protect stage setup and configuration for LangChain integration
"""
import os
from typing import Optional, List
from galileo.projects import Projects
from galileo.stages import Stages
from galileo_core.schemas.protect.ruleset import Ruleset
from galileo_core.schemas.protect.rule import Rule, RuleOperator
from galileo_core.schemas.protect.action import OverrideAction


# Map user-friendly metric names to the Protect API scorer names.
#
# IMPORTANT: The Protect API (promptgalileo) uses different names than the SDK
# (galileo_core).  The API members are e.g. "toxicity" / "pii" for output
# metrics, NOT "output_toxicity" / "output_pii".  We map to raw strings here
# because Rule.metric is a plain str that must match the API-side
# promptgalileo.ScorerName member name.
#
# Both the canonical API name (e.g. "toxicity") and the SDK-style alias
# (e.g. "output_toxicity") are included so config authors can use either.
METRIC_NAME_TO_API_SCORER: dict[str, str] = {
    # Input-side (same name in both SDK and API)
    "prompt_injection": "prompt_injection",
    "input_pii": "input_pii",
    "input_toxicity": "input_toxicity",
    "input_sexist": "input_sexist",
    "input_sexism": "input_sexist",
    "input_tone": "input_tone",
    # Output-side — API name has no "output_" prefix
    "pii": "pii",
    "output_pii": "pii",
    "toxicity": "toxicity",
    "output_toxicity": "toxicity",
    "sexist": "sexist",
    "output_sexist": "sexist",
    "output_sexism": "sexist",
    "tone": "tone",
    "output_tone": "tone",
    # Agentic / other
    "tool_error_rate": "tool_error_rate",
    "tool_selection_quality": "tool_selection_quality",
}

# Map string operators to RuleOperator enums
OPERATOR_MAP = {
    "gt": RuleOperator.gt,
    "lt": RuleOperator.lt,
    "gte": RuleOperator.gte,
    "lte": RuleOperator.lte,
    "eq": RuleOperator.eq,
    "neq": RuleOperator.neq,
    "any": RuleOperator.any,
    "all": RuleOperator.all,
    "contains": RuleOperator.contains,
    "empty": RuleOperator.empty,
    "not_empty": RuleOperator.not_empty,
}


def get_or_create_protect_stage(project_name: str, stage_name: Optional[str] = None) -> str:
    """
    Get or create a Protect stage for the project.
    
    Args:
        project_name: Name of the Galileo project
        stage_name: Optional stage name (defaults to "protect-prompt-injection-stage")
        
    Returns:
        Stage ID string
    """
    if stage_name is None:
        stage_name = os.environ.get("GALILEO_STAGE", "protect-prompt-injection-stage")
    
    # Get or create project
    project = Projects().get(name=project_name)
    project_id = project.id
    
    # Get or create stage
    try:
        stage = Stages().get(project_name=project_name, stage_name=stage_name)
        if stage is None:
            raise Exception("Stage not found")
    except Exception:
        # Stage doesn't exist, create it
        print(f"Creating stage: {stage_name}")
        stage = Stages().create(name=stage_name, project_name=project_name)
    
    return stage.id


def create_rule_from_config(metric_config: dict) -> Optional[Rule]:
    """
    Create a Rule object from metric configuration.
    
    Args:
        metric_config: Dict containing:
            - name: Metric name (e.g., "prompt_injection", "input_toxicity")
            - operator: Operator string (e.g., "any", "gt", "lt")
            - target_values: List of categories (for categorical metrics)
            - threshold: Numerical threshold (for numerical metrics)
    
    Returns:
        Rule object or None if invalid config
    """
    metric_name = metric_config.get("name")
    operator_str = metric_config.get("operator")
    
    if not metric_name or not operator_str:
        return None
    
    # Resolve to the API-side scorer name, or pass through for custom metrics
    metric = METRIC_NAME_TO_API_SCORER.get(metric_name, metric_name)
    
    # Get the operator
    operator = OPERATOR_MAP.get(operator_str)
    if operator is None:
        return None
    
    # Get target value based on metric type
    # Categorical metrics use target_values (list)
    # Numerical metrics use threshold (float)
    if "target_values" in metric_config:
        target_value = metric_config["target_values"]
    elif "threshold" in metric_config:
        target_value = metric_config["threshold"]
    else:
        # For empty/not_empty operators, no target value needed
        target_value = None
    
    return Rule(
        metric=metric,
        operator=operator,
        target_value=target_value
    )


def create_rulesets_from_config(
    domain_config: Optional[dict] = None,
    section: str = "protect",
) -> List[Ruleset]:
    """
    Create Ruleset objects from domain configuration.

    Args:
        domain_config: Optional domain config dict.
        section: Top-level key to read from the config. Use "protect_input" for the
                 pre-LLM node (payload has input only) and "protect_output" for the
                 post-LLM node (payload has both input and output). Defaults to
                 "protect" for backwards compatibility with single-section configs.

    Returns:
        List of Ruleset objects configured from the specified section.
    """
    protect_config = {}
    if domain_config:
        protect_config = domain_config.get(section, {})
    
    # Get metrics configuration - no fallback, must be explicitly configured
    metrics_config = protect_config.get("metrics", [])
    
    # Create rules from metric configurations
    rules = []
    for metric_config in metrics_config:
        rule = create_rule_from_config(metric_config)
        if rule:
            rules.append(rule)
    
    if not rules:
        return []
    
    # Get custom responses from domain config - no fallback, must be explicitly configured
    custom_responses = protect_config.get("messages", [])
    
    # Create ruleset with the rules and override action
    ruleset = Ruleset(
        rules=rules,
        action=OverrideAction(
            choices=custom_responses
        ),
    )
    
    return [ruleset]

