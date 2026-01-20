"""
Thinking/Reasoning Engine for RKLLM Chat System

Implements chain-of-thought and step-by-step reasoning patterns
to encourage the model to think through problems carefully.

Features:
- Chain-of-thought prompt injection
- Response parsing for thinking steps
- Thinking display formatting for UI
- Reasoning trace extraction
"""

import re
from typing import Dict, Optional, List, Tuple
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ThinkingEngine:
    """Engine for injecting and extracting thinking/reasoning."""
    
    # Prompt templates for different reasoning patterns
    CHAIN_OF_THOUGHT_TEMPLATE = """Let's think through this step-by-step:

Question: {query}

Step 1: Identify the key information
Step 2: Determine what we need to find
Step 3: Work through the reasoning
Step 4: Verify our conclusion

Reasoning Process:
"""
    
    STRUCTURED_THINKING_TEMPLATE = """Please provide a structured response:

Question: {query}

Think about:
1. What are the relevant facts or assumptions?
2. What is the core problem or question?
3. What are possible approaches?
4. What is the best solution?
5. Why is this the best approach?

Analysis:
"""
    
    DETAILED_EXPLANATION_TEMPLATE = """Explain this in detail with reasoning:

Question: {query}

Please include:
- Your initial understanding
- Key considerations
- Step-by-step explanation
- Conclusion and reasoning

Detailed Response:
"""
    
    def __init__(self, enable_thinking: bool = True):
        """Initialize thinking engine."""
        self.enabled = enable_thinking
        logger.info(f"💭 ThinkingEngine initialized (enabled: {enable_thinking})")
    
    def enable(self) -> None:
        """Enable thinking mode."""
        self.enabled = True
        logger.info("✅ Thinking mode enabled")
    
    def disable(self) -> None:
        """Disable thinking mode."""
        self.enabled = False
        logger.info("❌ Thinking mode disabled")
    
    def inject_thinking_prompt(
        self,
        user_message: str,
        pattern: str = "chain_of_thought"
    ) -> str:
        """
        Inject thinking prompt into user message.
        
        Args:
            user_message: Original user message/question
            pattern: Which thinking pattern to use
                   ("chain_of_thought", "structured", "detailed")
        
        Returns:
            Enhanced prompt with thinking instructions
        """
        
        if not self.enabled:
            return user_message
        
        # Select template based on pattern
        templates = {
            "chain_of_thought": self.CHAIN_OF_THOUGHT_TEMPLATE,
            "structured": self.STRUCTURED_THINKING_TEMPLATE,
            "detailed": self.DETAILED_EXPLANATION_TEMPLATE,
        }
        
        template = templates.get(pattern, self.CHAIN_OF_THOUGHT_TEMPLATE)
        
        enhanced_prompt = template.format(query=user_message)
        
        logger.info(f"💭 Thinking prompt injected (pattern: {pattern})")
        
        return enhanced_prompt
    
    def extract_thinking_steps(self, response: str) -> List[str]:
        """
        Extract thinking steps from model response.
        
        Looks for patterns like "Step 1:", "Therefore:", etc.
        """
        
        steps = []
        
        # Pattern 1: Numbered steps
        step_pattern = r'Step \d+:.*?(?=Step \d+:|Therefore:|Conclusion:|$)'
        matches = re.finditer(step_pattern, response, re.DOTALL | re.IGNORECASE)
        for match in matches:
            step_text = match.group(0).strip()
            if step_text:
                steps.append(step_text)
        
        # Pattern 2: Bullet points
        if not steps:
            bullet_pattern = r'^[-•*]\s+.*?$'
            matches = re.finditer(bullet_pattern, response, re.MULTILINE)
            for match in matches:
                step_text = match.group(0).strip()
                if step_text:
                    steps.append(step_text)
        
        # Pattern 3: Numbered list
        if not steps:
            numbered_pattern = r'^\d+\.\s+.*?$'
            matches = re.finditer(numbered_pattern, response, re.MULTILINE)
            for match in matches:
                step_text = match.group(0).strip()
                if step_text:
                    steps.append(step_text)
        
        return steps
    
    def extract_conclusion(self, response: str) -> Optional[str]:
        """
        Extract conclusion or final answer from response.
        
        Looks for patterns like "Therefore:", "Conclusion:", "Answer:"
        """
        
        conclusion_patterns = [
            r'(?:Therefore|In conclusion|Conclusion|Answer|Result):\s*(.*?)(?=\n\n|$)',
            r'(?:^|\n)Final Answer:\s*(.*?)(?:\n|$)',
            r'(?:^|\n)Summary:\s*(.*?)(?:\n|$)',
        ]
        
        for pattern in conclusion_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                conclusion = match.group(1).strip()
                if conclusion and len(conclusion) > 20:  # Meaningful conclusion
                    return conclusion
        
        # Fallback: take last paragraph
        paragraphs = [p.strip() for p in response.split('\n\n') if p.strip()]
        if paragraphs:
            return paragraphs[-1]
        
        return None
    
    def separate_thinking_from_answer(self, response: str) -> Tuple[str, str]:
        """
        Separate thinking process from final answer.
        
        Returns: (thinking_text, answer_text)
        """
        
        # Pattern 1: XML-like tags
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        if thinking_match:
            thinking = thinking_match.group(1).strip()
            answer = response.replace(thinking_match.group(0), "").strip()
            return thinking, answer
        
        # Pattern 2: Explicit separators
        if "---ANSWER---" in response:
            parts = response.split("---ANSWER---", 1)
            thinking = parts[0].replace("---THINKING---", "").strip()
            answer = parts[1].strip() if len(parts) > 1 else ""
            return thinking, answer
        
        # Pattern 3: Look for conclusion marker
        steps = self.extract_thinking_steps(response)
        if steps:
            conclusion = self.extract_conclusion(response)
            thinking_text = "\n".join(steps)
            answer_text = conclusion or response
            return thinking_text, answer_text
        
        # Fallback: no clear separation
        return "", response
    
    def format_thinking_for_display(self, thinking_text: str, max_chars: int = 500) -> str:
        """
        Format thinking text for UI display (e.g., in collapsed section).
        
        Args:
            thinking_text: Raw thinking text from model
            max_chars: Maximum characters to show (rest in details)
        
        Returns:
            Formatted thinking for UI
        """
        
        if not thinking_text:
            return ""
        
        # Clean up text
        cleaned = thinking_text.strip()
        
        # Extract steps for better display
        steps = self.extract_thinking_steps(cleaned)
        
        if steps and len(steps) > 0:
            # Format as collapsible section
            steps_display = "\n".join([f"• {step[:100]}" for step in steps[:5]])
            
            if len(cleaned) > max_chars:
                return f"""<details>
<summary>💭 Model Thinking ({len(steps)} steps)</summary>

{steps_display}

*(Full thinking truncated)*
</details>"""
            else:
                return f"""<details>
<summary>💭 Model Thinking ({len(steps)} steps)</summary>

{cleaned}
</details>"""
        else:
            # No clear steps, just show as quote
            if len(cleaned) > max_chars:
                preview = cleaned[:max_chars] + "..."
                return f"> **Thinking:** {preview}"
            else:
                return f"> **Thinking:** {cleaned}"
    
    def parse_complex_response(self, response: str) -> Dict:
        """
        Parse complex response with thinking and answer.
        
        Returns: {
            'thinking': str,
            'answer': str,
            'steps': List[str],
            'conclusion': str,
        }
        """
        
        thinking, answer = self.separate_thinking_from_answer(response)
        steps = self.extract_thinking_steps(response)
        conclusion = self.extract_conclusion(response)
        
        return {
            'thinking': thinking,
            'answer': answer or response,
            'steps': steps,
            'conclusion': conclusion or "No explicit conclusion",
        }
    
    def validate_reasoning(self, response: str) -> Dict:
        """
        Validate quality of reasoning in response.
        
        Returns: {
            'has_thinking': bool,
            'num_steps': int,
            'has_conclusion': bool,
            'quality_score': float (0-1),
        }
        """
        
        parsed = self.parse_complex_response(response)
        
        has_thinking = bool(parsed['thinking'])
        num_steps = len(parsed['steps'])
        has_conclusion = parsed['conclusion'] != "No explicit conclusion"
        
        # Calculate quality score
        quality_score = 0.0
        if has_thinking:
            quality_score += 0.3
        if num_steps >= 3:
            quality_score += 0.4
        elif num_steps >= 1:
            quality_score += 0.2
        if has_conclusion:
            quality_score += 0.3
        
        return {
            'has_thinking': has_thinking,
            'num_steps': num_steps,
            'has_conclusion': has_conclusion,
            'quality_score': min(quality_score, 1.0),
        }


# Global instance
_thinking_engine: Optional[ThinkingEngine] = None


def get_thinking_engine() -> ThinkingEngine:
    """Get or create global thinking engine instance."""
    global _thinking_engine
    
    if _thinking_engine is None:
        _thinking_engine = ThinkingEngine(enable_thinking=True)
    
    return _thinking_engine


def inject_thinking(
    user_message: str,
    pattern: str = "chain_of_thought"
) -> str:
    """Convenience function to inject thinking prompt."""
    return get_thinking_engine().inject_thinking_prompt(user_message, pattern)


def parse_thinking_response(response: str) -> Dict:
    """Convenience function to parse response with thinking."""
    return get_thinking_engine().parse_complex_response(response)


def format_thinking_display(thinking_text: str) -> str:
    """Convenience function to format thinking for UI."""
    return get_thinking_engine().format_thinking_for_display(thinking_text)
