"""
Galileo Guardrails Configuration

Implements comprehensive guardrails for:
- Input: PII, Sexism, Toxicity filtering
- Output: PII, Sexism, Toxicity filtering
- Context Adherence: Block trades if < 70% threshold (hallucination detection)

Usage:
    from guardrails_config import GuardrailsManager
    
    manager = GuardrailsManager(enabled=True)
    result = await manager.check_input(user_query)
    result = await manager.check_output(response, context, input)
    result = await manager.check_trade(trade_details, context, input)
"""
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Import Galileo Protect
try:
    from galileo import GalileoScorers
    from galileo.protect import ainvoke_protect, invoke_protect
    from galileo_core.schemas.protect.payload import Payload
    from galileo_core.schemas.protect.rule import Rule, RuleOperator
    from galileo_core.schemas.protect.ruleset import Ruleset
    from galileo_core.schemas.protect.action import OverrideAction
    from galileo_core.schemas.protect.execution_status import ExecutionStatus
    PROTECT_AVAILABLE = True
except ImportError:
    print("⚠️  Galileo Protect not available. Install with: pip install galileo-protect")
    PROTECT_AVAILABLE = False


@dataclass
class GuardrailResult:
    """Result from guardrail check"""
    passed: bool
    blocked_by: Optional[str] = None
    message: Optional[str] = None
    original_response: Optional[str] = None
    score: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class GuardrailsManager:
    """
    Manages Galileo Guardrails for the finance agent
    
    Features:
    - Input filtering (PII, Sexism, Toxicity)
    - Output filtering (PII, Sexism, Toxicity)
    - Context adherence checking (hallucination detection)
    - Special handling for trade actions
    """
    
    def __init__(self, enabled: bool = True):
        """
        Initialize guardrails manager
        
        Args:
            enabled: Whether guardrails are enabled globally
        """
        self.enabled = enabled and PROTECT_AVAILABLE
        
        if not PROTECT_AVAILABLE:
            print("⚠️  Guardrails disabled - Galileo Protect not available")
            self.enabled = False
        
        # Guardrail thresholds
        self.pii_threshold = 0.5  # Block if PII confidence > 50%
        self.sexism_threshold = 0.5  # Block if sexism score > 50%
        self.toxicity_threshold = 0.5  # Block if toxicity score > 50%
        self.context_adherence_threshold = 0.70  # Block trades if < 70%
        
        # Shield icon for blocked messages
        self.shield_icon = "🛡️"
        
        # Get project name from environment
        self.project_name = os.getenv("GALILEO_PROJECT", "guardrails-demo")
        
        # Stats
        self.stats = {
            "input_checks": 0,
            "input_blocks": 0,
            "output_checks": 0,
            "output_blocks": 0,
            "trade_checks": 0,
            "trade_blocks": 0
        }
    
    def is_enabled(self) -> bool:
        """Check if guardrails are enabled"""
        return self.enabled
    
    def enable(self):
        """Enable guardrails"""
        if PROTECT_AVAILABLE:
            self.enabled = True
            print("✅ Guardrails enabled")
        else:
            print("⚠️  Cannot enable - Galileo Protect not available")
    
    def disable(self):
        """Disable guardrails"""
        self.enabled = False
        print("🔓 Guardrails disabled")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrails statistics"""
        return {
            **self.stats,
            "enabled": self.enabled,
            "block_rate": (
                (self.stats["input_blocks"] + self.stats["output_blocks"] + self.stats["trade_blocks"]) /
                max(1, self.stats["input_checks"] + self.stats["output_checks"] + self.stats["trade_checks"])
            ) * 100
        }
    
    def reset_stats(self):
        """Reset statistics"""
        for key in self.stats:
            self.stats[key] = 0
    
    # ==================== INPUT GUARDRAILS ====================
    
    async def check_input_async(self, user_input: str) -> GuardrailResult:
        """
        Check user input for PII, Sexism, and Toxicity
        
        Args:
            user_input: The user's query
            
        Returns:
            GuardrailResult with pass/fail and details
        """
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        self.stats["input_checks"] += 1
        
        try:
            # Create rulesets for input checking
            rulesets = self._create_input_rulesets()
            
            # Create payload
            payload = Payload(input=user_input)
            
            # Invoke protect
            response = await ainvoke_protect(
                payload=payload,
                project_name=self.project_name,
                stage_name="input_filtering",
                prioritized_rulesets=rulesets
            )
            
            # Check if guardrail was triggered
            if response.status == ExecutionStatus.triggered:
                self.stats["input_blocks"] += 1
                
                # Determine what was blocked from the response
                blocked_by = self._get_blocked_reason_from_response(response, "input")
                
                return GuardrailResult(
                    passed=False,
                    blocked_by=blocked_by,
                    message=self._get_input_block_message(blocked_by),
                    original_response=user_input,
                    details={"status": str(response.status), "text": response.text}
                )
            
            return GuardrailResult(passed=True)
            
        except Exception as e:
            print(f"⚠️  Error checking input guardrails: {e}")
            # Fail open - allow input if error
            return GuardrailResult(passed=True)
    
    def check_input(self, user_input: str) -> GuardrailResult:
        """Synchronous version of check_input_async"""
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        self.stats["input_checks"] += 1
        
        try:
            # Create rulesets for input checking
            rulesets = self._create_input_rulesets()
            
            # Create payload
            payload = Payload(input=user_input)
            
            # Invoke protect (synchronous)
            response = invoke_protect(
                payload=payload,
                project_name=self.project_name,
                stage_name="input_filtering",
                prioritized_rulesets=rulesets
            )
            
            # Check if guardrail was triggered
            if response.status == ExecutionStatus.triggered:
                self.stats["input_blocks"] += 1
                
                # Determine what was blocked from the response
                blocked_by = self._get_blocked_reason_from_response(response, "input")
                
                return GuardrailResult(
                    passed=False,
                    blocked_by=blocked_by,
                    message=self._get_input_block_message(blocked_by),
                    original_response=user_input,
                    details={"status": str(response.status), "text": response.text}
                )
            
            return GuardrailResult(passed=True)
            
        except Exception as e:
            print(f"⚠️  Error checking input guardrails: {e}")
            # Fail open - allow input if error
            return GuardrailResult(passed=True)
    
    # ==================== OUTPUT GUARDRAILS ====================
    
    async def check_output_async(
        self,
        output: str,
        context: Optional[str] = None,
        user_input: Optional[str] = None
    ) -> GuardrailResult:
        """
        Check output for PII, Sexism, and Toxicity
        
        Args:
            output: The agent's response
            context: Context used for generation (optional)
            user_input: Original user input (optional)
            
        Returns:
            GuardrailResult with pass/fail and details
        """
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        self.stats["output_checks"] += 1
        
        try:
            # Create rulesets for output checking
            rulesets = self._create_output_rulesets()
            
            # Create payload
            payload = Payload(
                output=output,
                input=user_input,
                context=context
            )
            
            # Invoke protect
            response = await ainvoke_protect(
                payload=payload,
                project_name=self.project_name,
                stage_name="output_filtering",
                prioritized_rulesets=rulesets
            )
            
            # Check if guardrail was triggered
            if response.status == ExecutionStatus.triggered:
                self.stats["output_blocks"] += 1
                
                # Determine what was blocked from the response
                blocked_by = self._get_blocked_reason_from_response(response, "output")
                
                return GuardrailResult(
                    passed=False,
                    blocked_by=blocked_by,
                    message=self._get_output_block_message(blocked_by),
                    original_response=output,
                    details={"status": str(response.status), "text": response.text}
                )
            
            return GuardrailResult(passed=True)
            
        except Exception as e:
            print(f"⚠️  Error checking output guardrails: {e}")
            # Fail open - allow output if error
            return GuardrailResult(passed=True)
    
    def check_output(
        self,
        output: str,
        context: Optional[str] = None,
        user_input: Optional[str] = None
    ) -> GuardrailResult:
        """Synchronous version of check_output_async"""
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        self.stats["output_checks"] += 1
        
        try:
            # Create rulesets for output checking
            rulesets = self._create_output_rulesets()
            
            # Create payload
            payload = Payload(
                output=output,
                input=user_input,
                context=context
            )
            
            # Invoke protect (synchronous)
            response = invoke_protect(
                payload=payload,
                project_name=self.project_name,
                stage_name="output_filtering",
                prioritized_rulesets=rulesets
            )
            
            # Check if guardrail was triggered
            if response.status == ExecutionStatus.triggered:
                self.stats["output_blocks"] += 1
                
                # Determine what was blocked from the response
                blocked_by = self._get_blocked_reason_from_response(response, "output")
                
                return GuardrailResult(
                    passed=False,
                    blocked_by=blocked_by,
                    message=self._get_output_block_message(blocked_by),
                    original_response=output,
                    details={"status": str(response.status), "text": response.text}
                )
            
            return GuardrailResult(passed=True)
            
        except Exception as e:
            print(f"⚠️  Error checking output guardrails: {e}")
            # Fail open - allow output if error
            return GuardrailResult(passed=True)
    
    # ==================== TRADE GUARDRAILS ====================
    
    async def check_trade_async(
        self,
        trade_output: str,
        context: str,
        user_input: str
    ) -> GuardrailResult:
        """
        Check trade action for context adherence (hallucination detection)
        
        Blocks trade if context adherence < 70%
        
        Args:
            trade_output: The agent's trade confirmation message
            context: Context used for the trade decision
            user_input: Original user input
            
        Returns:
            GuardrailResult with pass/fail and details
        """
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        self.stats["trade_checks"] += 1
        
        try:
            # Create ruleset for context adherence
            ruleset = self._create_trade_ruleset()
            
            # Create payload
            payload = Payload(
                output=trade_output,
                context=context,
                input=user_input
            )
            
            # Invoke protect
            response = await ainvoke_protect(
                payload=payload,
                project_name=self.project_name,
                stage_name="trade_validation",
                prioritized_rulesets=[ruleset]
            )
            
            # Check if guardrail was triggered
            if response.status == ExecutionStatus.triggered:
                self.stats["trade_blocks"] += 1
                
                # Extract context adherence score from response text if available
                score = self._extract_context_adherence_score(response)
                
                return GuardrailResult(
                    passed=False,
                    blocked_by="Low Context Adherence (Potential Hallucination)",
                    message=self._get_trade_block_message(score),
                    original_response=trade_output,
                    score=score,
                    details={"status": str(response.status), "text": response.text}
                )
            
            return GuardrailResult(passed=True)
            
        except Exception as e:
            print(f"⚠️  Error checking trade guardrails: {e}")
            # Fail closed for trades - block if error
            self.stats["trade_blocks"] += 1
            return GuardrailResult(
                passed=False,
                blocked_by="Error",
                message=f"{self.shield_icon} **Trade Blocked**: Guardrail error - {str(e)}",
                original_response=trade_output
            )
    
    def check_trade(
        self,
        trade_output: str,
        context: str,
        user_input: str
    ) -> GuardrailResult:
        """Synchronous version of check_trade_async"""
        if not self.enabled:
            return GuardrailResult(passed=True)
        
        self.stats["trade_checks"] += 1
        
        try:
            # Create ruleset for context adherence
            ruleset = self._create_trade_ruleset()
            
            # Create payload
            payload = Payload(
                output=trade_output,
                context=context,
                input=user_input
            )
            
            # Invoke protect (synchronous)
            response = invoke_protect(
                payload=payload,
                project_name=self.project_name,
                stage_name="trade_validation",
                prioritized_rulesets=[ruleset]
            )
            
            # Check if guardrail was triggered
            if response.status == ExecutionStatus.triggered:
                self.stats["trade_blocks"] += 1
                
                # Extract context adherence score from response text if available
                score = self._extract_context_adherence_score(response)
                
                return GuardrailResult(
                    passed=False,
                    blocked_by="Low Context Adherence (Potential Hallucination)",
                    message=self._get_trade_block_message(score),
                    original_response=trade_output,
                    score=score,
                    details={"status": str(response.status), "text": response.text}
                )
            
            return GuardrailResult(passed=True)
            
        except Exception as e:
            print(f"⚠️  Error checking trade guardrails: {e}")
            # Fail closed for trades - block if error
            self.stats["trade_blocks"] += 1
            return GuardrailResult(
                passed=False,
                blocked_by="Error",
                message=f"{self.shield_icon} **Trade Blocked**: Guardrail error - {str(e)}",
                original_response=trade_output
            )
    
    # ==================== RULESET CREATION ====================
    
    def _create_input_rulesets(self) -> List[Ruleset]:
        """Create rulesets for input filtering"""
        rulesets = []
        
        # PII Rule
        pii_rule = Rule(
            metric=GalileoScorers.input_pii,
            operator=RuleOperator.gt,
            target_value=self.pii_threshold
        )
        rulesets.append(Ruleset(rules=[pii_rule], description="Detect PII in input"))
        
        # Sexism Rule
        sexism_rule = Rule(
            metric=GalileoScorers.input_sexism,
            operator=RuleOperator.gt,
            target_value=self.sexism_threshold
        )
        rulesets.append(Ruleset(rules=[sexism_rule], description="Detect sexism in input"))
        
        # Toxicity Rule
        toxicity_rule = Rule(
            metric=GalileoScorers.input_toxicity,
            operator=RuleOperator.gt,
            target_value=self.toxicity_threshold
        )
        rulesets.append(Ruleset(rules=[toxicity_rule], description="Detect toxicity in input"))
        
        return rulesets
    
    def _create_output_rulesets(self) -> List[Ruleset]:
        """Create rulesets for output filtering"""
        rulesets = []
        
        # PII Rule
        pii_rule = Rule(
            metric=GalileoScorers.output_pii,
            operator=RuleOperator.gt,
            target_value=self.pii_threshold
        )
        rulesets.append(Ruleset(rules=[pii_rule], description="Detect PII in output"))
        
        # Sexism Rule
        sexism_rule = Rule(
            metric=GalileoScorers.output_sexism,
            operator=RuleOperator.gt,
            target_value=self.sexism_threshold
        )
        rulesets.append(Ruleset(rules=[sexism_rule], description="Detect sexism in output"))
        
        # Toxicity Rule
        toxicity_rule = Rule(
            metric=GalileoScorers.output_toxicity,
            operator=RuleOperator.gt,
            target_value=self.toxicity_threshold
        )
        rulesets.append(Ruleset(rules=[toxicity_rule], description="Detect toxicity in output"))
        
        return rulesets
    
    def _create_trade_ruleset(self) -> Ruleset:
        """Create ruleset for trade validation (context adherence)"""
        rule = Rule(
            metric=GalileoScorers.context_adherence,
            operator=RuleOperator.lt,
            target_value=self.context_adherence_threshold
        )
        return Ruleset(
            rules=[rule],
            description=f"Block trades if context adherence < {self.context_adherence_threshold*100}%"
        )
    
    # ==================== HELPER METHODS ====================
    
    def _get_blocked_reason_from_response(self, response: Any, check_type: str) -> str:
        """
        Determine what caused the block from the response
        
        Since multiple rulesets may be checked and we don't know which one triggered,
        we examine the response text for clues and provide descriptive feedback.
        
        Args:
            response: The Galileo Protect response
            check_type: Type of check ("input" or "output")
            
        Returns:
            Reason for blocking
        """
        # Try to parse response text for specific detections
        if hasattr(response, 'text') and response.text:
            text_lower = response.text.lower()
            
            # Check for specific mentions in response
            if any(keyword in text_lower for keyword in ['pii', 'personally identifiable', 'ssn', 'social security', 'account number', 'credit card']):
                return "PII Detected"
            if any(keyword in text_lower for keyword in ['sexism', 'sexist', 'discriminat']):
                return "Sexism Detected"  
            if any(keyword in text_lower for keyword in ['toxic', 'toxicity', 'harmful', 'offensive', 'abusive']):
                return "Toxicity Detected"
            if any(keyword in text_lower for keyword in ['context', 'adherence', 'hallucin']):
                return "Low Context Adherence"
        
        # No specific detection found in text, return descriptive generic message
        if check_type == "input":
            return "Policy Violation (Safety Check)"
        elif check_type == "output":
            return "Policy Violation (Content Check)"
        else:
            return "Policy Violation"
    
    def _get_input_block_message(self, blocked_by: str) -> str:
        """Get message for blocked input"""
        messages = {
            "PII Detected": f"{self.shield_icon} **Input Blocked - PII Detected**\n\nYour message contains personally identifiable information (PII) such as:\n- Account numbers\n- Social Security Numbers\n- Credit card information\n- Personal addresses or phone numbers\n\nPlease rephrase your message without including this sensitive data.",
            
            "Sexism Detected": f"{self.shield_icon} **Input Blocked - Inappropriate Content**\n\nYour message contains content that may be discriminatory or inappropriate.\n\nPlease rephrase your message respectfully and without discriminatory language.",
            
            "Toxicity Detected": f"{self.shield_icon} **Input Blocked - Harmful Content**\n\nYour message contains toxic, offensive, or harmful language.\n\nPlease rephrase your message in a polite and constructive manner.",
            
            "Policy Violation (Safety Check)": f"{self.shield_icon} **Input Blocked - Safety Filter**\n\nYour message was flagged by our content safety filters. This could be due to:\n- Sensitive personal information (PII)\n- Inappropriate or discriminatory content\n- Toxic or harmful language\n\nPlease rephrase your message and try again.",
        }
        return messages.get(blocked_by, f"{self.shield_icon} **Input Blocked**: Your message was blocked by our safety filters. Please rephrase and try again.")
    
    def _get_output_block_message(self, blocked_by: str) -> str:
        """Get message for blocked output"""
        messages = {
            "PII Detected": f"{self.shield_icon} **Response Blocked - PII Detected**\n\nThe AI's response contained sensitive information that has been blocked for your protection:\n- Account numbers\n- Social Security Numbers  \n- Credit card information\n- Personal contact details\n\nI apologize for the inconvenience. Please try rephrasing your question or ask for information in a different way.",
            
            "Sexism Detected": f"{self.shield_icon} **Response Blocked - Inappropriate Content**\n\nThe AI's response was blocked because it contained inappropriate or discriminatory content.\n\nI apologize for this. Please try rephrasing your question and I'll provide a more appropriate response.",
            
            "Toxicity Detected": f"{self.shield_icon} **Response Blocked - Harmful Content**\n\nThe AI's response was blocked because it contained potentially harmful or offensive content.\n\nI apologize for this issue. Please try asking your question in a different way.",
            
            "Policy Violation (Content Check)": f"{self.shield_icon} **Response Blocked - Content Filter**\n\nThe AI's response was flagged by content safety filters. This could be due to:\n- Sensitive information exposure (PII)\n- Inappropriate or discriminatory content\n- Potentially harmful content\n\nI apologize for the inconvenience. Please try rephrasing your question.",
        }
        return messages.get(blocked_by, f"{self.shield_icon} **Response Blocked**: The response was blocked by content safety filters. Please try rephrasing your question.")
    
    def _get_trade_block_message(self, score: Optional[float] = None) -> str:
        """Get message for blocked trade"""
        if score is not None:
            return f"""{self.shield_icon} **Trade Blocked - Low Confidence Detected**

**Context Adherence Score: {score:.1%}**
(Threshold: {self.context_adherence_threshold:.0%})

The trade details appear to be inconsistent with the conversation context. This could indicate:
- Incorrect stock symbols or quantities
- Misinterpreted price information
- Hallucinated trade parameters

Please verify the trade details and try again with explicit confirmation."""
        
        return f"""{self.shield_icon} **Trade Blocked - Low Confidence Detected**

The trade details have low context adherence (below {self.context_adherence_threshold:.0%} threshold).

This safety check prevents potentially incorrect trades. Please:
1. Verify the stock symbol is correct
2. Confirm the quantity and price
3. Restate your trade request clearly"""
    
    def _extract_context_adherence_score(self, response: Any) -> Optional[float]:
        """
        Extract context adherence score from response
        
        The response text may contain the score, or we can try to parse it.
        For now, return None as we don't have direct access to metric values.
        """
        try:
            # Try to parse score from response text if it contains it
            if hasattr(response, 'text') and response.text:
                text = response.text.lower()
                # Look for patterns like "score: 0.45" or "adherence: 0.45"
                import re
                patterns = [
                    r'score[:\s]+([0-9.]+)',
                    r'adherence[:\s]+([0-9.]+)',
                    r'confidence[:\s]+([0-9.]+)'
                ]
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        return float(match.group(1))
        except:
            pass
        return None


# Singleton instance
_guardrails_manager: Optional[GuardrailsManager] = None


def get_guardrails_manager() -> GuardrailsManager:
    """Get or create the singleton guardrails manager"""
    global _guardrails_manager
    if _guardrails_manager is None:
        # Check environment variable
        enabled = os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true"
        _guardrails_manager = GuardrailsManager(enabled=enabled)
    return _guardrails_manager


def reset_guardrails_manager():
    """Reset the singleton (useful for testing)"""
    global _guardrails_manager
    _guardrails_manager = None

