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
from galileo_core.schemas.shared.scorers.scorer_name import ScorerName as GalileoScorers


# Map string metric names to GalileoScorers enums
METRIC_NAME_TO_SCORER = {
    "prompt_injection": GalileoScorers.prompt_injection,
    "input_pii": GalileoScorers.input_pii,
    "output_pii": GalileoScorers.output_pii,
    "input_toxicity": GalileoScorers.input_toxicity,
    "output_toxicity": GalileoScorers.output_toxicity,
    "input_sexism": GalileoScorers.input_sexism,
    "output_sexism": GalileoScorers.output_sexism,
    "input_tone": GalileoScorers.input_tone,
    "output_tone": GalileoScorers.output_tone,
    "context_adherence": GalileoScorers.context_adherence,
    "completeness": GalileoScorers.completeness,
    "action_advancement": GalileoScorers.action_advancement,
    "action_completion": GalileoScorers.action_completion,
    "tool_error_rate": GalileoScorers.tool_error_rate,
    "tool_selection_quality": GalileoScorers.tool_selection_quality,
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
        stage = Stages().get(project_id=project_id, stage_name=stage_name)
        if stage is None:
            raise Exception("Stage not found")
    except Exception:
        # Stage doesn't exist, create it
        print(f"Creating stage: {stage_name}")
        stage = Stages().create(name=stage_name, project_id=project_id)
    
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
    
    # Get the GalileoScorer enum or use string for custom metrics
    if metric_name in METRIC_NAME_TO_SCORER:
        metric = METRIC_NAME_TO_SCORER[metric_name]
    else:
        # Support custom metrics by name
        metric = metric_name
    
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


def create_rulesets_from_config(domain_config: Optional[dict] = None) -> List[Ruleset]:
    """
    Create Ruleset objects from domain configuration.
    
    Args:
        domain_config: Optional domain config dict containing protect settings with:
            - metrics: List of metric configurations
            - messages: List of custom response messages
    
    Returns:
        List of Ruleset objects configured from domain config
    """
    # Get protect config from domain config if provided
    protect_config = {}
    if domain_config:
        protect_config = domain_config.get("protect", {})
    
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

