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

import logging
import re
from typing import Dict, List, Optional, Tuple

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
    
    def injectThinkingPrompt(
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
    
    def extractThinkingSteps(self, response: str) -> List[str]:
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
    
    def extractConclusion(self, response: str) -> Optional[str]:
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
    
    def separateThinkingFromAnswer(self, response: str) -> Tuple[str, str]:
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
        steps = self.extractThinkingSteps(response)
        if steps:
            conclusion = self.extractConclusion(response)
            thinking_text = "\n".join(steps)
            answer_text = conclusion or response
            return thinking_text, answer_text
        
        # Fallback: no clear separation
        return "", response
    
    def formatThinkingForDisplay(self, thinking_text: str, max_chars: int = 500) -> str:
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
        steps = self.extractThinkingSteps(cleaned)
        
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
    
    def parseComplexResponse(self, response: str) -> Dict:
        """
        Parse complex response with thinking and answer.
        
        Returns: {
            'thinking': str,
            'answer': str,
            'steps': List[str],
            'conclusion': str,
        }
        """
        
        thinking, answer = self.separateThinkingFromAnswer(response)
        steps = self.extractThinkingSteps(response)
        conclusion = self.extractConclusion(response)
        
        return {
            'thinking': thinking,
            'answer': answer or response,
            'steps': steps,
            'conclusion': conclusion or "No explicit conclusion",
        }
    
    def validateReasoning(self, response: str) -> Dict:
        """
        Validate quality of reasoning in response.
        
        Returns: {
            'has_thinking': bool,
            'num_steps': int,
            'has_conclusion': bool,
            'quality_score': float (0-1),
        }
        """
        
        parsed = self.parseComplexResponse(response)
        
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


def getThinkingEngine() -> ThinkingEngine:
    """Get or create global thinking engine instance."""
    global _thinking_engine
    
    if _thinking_engine is None:
        _thinking_engine = ThinkingEngine(enable_thinking=True)
    
    return _thinking_engine


def injectThinking(
    user_message: str,
    pattern: str = "chain_of_thought"
) -> str:
    """Convenience function to inject thinking prompt."""
    return getThinkingEngine().injectThinkingPrompt(user_message, pattern)


def parse_thinking_response(response: str) -> Dict:
    """Convenience function to parse response with thinking."""
    return getThinkingEngine().parseComplexResponse(response)


def format_thinking_display(thinking_text: str) -> str:
    """Convenience function to format thinking for UI."""
    return getThinkingEngine().formatThinkingForDisplay(thinking_text)


class LoopThinkingEngine:
    """
    Loop-based thinking engine that iteratively gathers information.
    
    Process:
    1. Analyze query and design steps
    2. Execute search/reasoning step
    3. Evaluate completeness
    4. Loop until information complete
    5. Generate final response
    """
    
    ANALYSIS_PROMPT = """Analyze this query and design steps to gather information:

        Query: {query}

        Please provide:
        1. What information is needed?
        2. What search queries would help?
        3. How many steps until complete?

        Analysis:
    """
    
    EVALUATION_PROMPT = """Evaluate if we have enough information:

        Query: {original_query}

        Information gathered so far:
        {gathered_info}

        Questions:
        1. Do we have enough information? (YES/NO)
        2. What additional information is needed?
        3. What should the next search query be?

        Evaluation:
    """
    
    def __init__(self, max_iterations: int = 3, info_threshold: int = 500):
        """
        Initialize loop thinking engine.
        
        Args:
            max_iterations: Maximum loop iterations
            info_threshold: Minimum characters of info to consider complete
        """
        self.max_iterations = max_iterations
        self.info_threshold = info_threshold
        logger.info(f"🔄 LoopThinkingEngine initialized (max_iter: {max_iterations})")
    
    def designSearchSteps(self, query: str) -> Dict:
        """
        Design steps to gather information for a query.
        
        Returns:
            {
                'steps': [...],
                'search_queries': [...],
                'estimated_iterations': int
            }
        """
        
        # Extract key aspects from query
        keywords = query.lower().split()
        
        # Determine complexity
        is_complex = len(keywords) > 5
        is_current = any(t in query.lower() for t in ['latest', 'recent', 'current', 'today'])
        
        steps = []
        queries = []
        iterations = 1
        
        if is_current:
            steps.append("Search for current information")
            queries.append(f"latest {' '.join(keywords[:3])}")
            iterations = 2
        else:
            steps.append("Search for general information")
            queries.append(' '.join(keywords[:5]))
        
        if is_complex:
            steps.append("Gather detailed context")
            iterations += 1
        
        logger.info(f"📋 Designed {len(steps)} steps for query")
        
        return {
            'steps': steps,
            'search_queries': queries,
            'estimated_iterations': min(iterations, self.max_iterations),
            'is_complex': is_complex,
            'is_current': is_current
        }
    
    def evaluateCompleteness(
        self,
        gathered_info: str,
        original_query: str,
        iteration: int
    ) -> Dict:
        """
        Evaluate if gathered information is complete.
        
        Returns:
            {
                'is_complete': bool,
                'confidence': float (0-1),
                'next_query': str or None,
                'reason': str
            }
        """
        
        info_length = len(gathered_info)
        
        # Simple heuristics
        is_sufficient_length = info_length >= self.info_threshold
        is_max_iterations = iteration >= self.max_iterations
        has_details = any(word in gathered_info.lower() for word in ['because', 'due to', 'result', 'leading'])
        
        is_complete = (is_sufficient_length and has_details) or is_max_iterations
        confidence = min(info_length / (self.info_threshold * 2), 1.0)
        
        reason = ""
        next_query = None
        
        if is_complete:
            reason = "Sufficient information gathered" if not is_max_iterations else "Max iterations reached"
        else:
            reason = "Need more details"
            # Suggest next search area
            if 'how' in original_query.lower():
                next_query = f"{original_query} explanation examples"
            elif 'why' in original_query.lower():
                next_query = f"{original_query} reasons causes"
            else:
                next_query = f"{original_query} detailed information"
        
        logger.info(f"📊 Completeness eval: complete={is_complete}, conf={confidence:.2f}")
        
        return {
            'is_complete': is_complete,
            'confidence': confidence,
            'next_query': next_query,
            'reason': reason,
            'info_length': info_length
        }
    
    def gatherInformationLoop(
        self,
        query: str,
        search_func,  # Function to perform searches
        info_extractor=None  # Optional function to extract info
    ) -> Dict:
        """
        Loop-based information gathering.
        
        Returns:
            {
                'gathered_info': str,
                'iterations': int,
                'search_queries': List[str],
                'completeness': Dict,
                'thinking_steps': List[str]
            }
        """
        
        gathered_info = ""
        search_queries = []
        thinking_steps = []
        
        # Step 1: Design search steps
        design = self.designSearchSteps(query)
        thinking_steps.append(f"Designed {design['estimated_iterations']} iterations")
        
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"\n🔄 Iteration {iteration}/{self.max_iterations}")
            
            # Determine search query
            if iteration == 1:
                # Use first designed query
                search_query = design['search_queries'][0] if design['search_queries'] else query
            else:
                # Evaluate and get next query
                eval_result = self.evaluateCompleteness(gathered_info, query, iteration - 1)
                if eval_result['is_complete']:
                    thinking_steps.append(f"Stopped at iteration {iteration}: {eval_result['reason']}")
                    break
                search_query = eval_result['next_query'] or query
            
            search_queries.append(search_query)
            thinking_steps.append(f"Iteration {iteration}: Searching '{search_query}'")
            
            # Perform search
            try:
                results = search_func(search_query, max_results=2)
                
                # Extract information from results
                for result in results:
                    content = result.get('full_content') or result.get('snippet', '')
                    if content:
                        gathered_info += "\n" + content
            
            except Exception as e:
                logger.warning(f"⚠️  Search failed at iteration {iteration}: {e}")
                thinking_steps.append(f"Search error at iteration {iteration}")
        
        # Final evaluation
        final_eval = self.evaluateCompleteness(gathered_info, query, iteration)
        thinking_steps.append(f"Final: {final_eval['reason']} (confidence: {final_eval['confidence']:.1%})")
        
        logger.info(f"✅ Information gathering complete in {iteration} iterations")
        
        return {
            'gathered_info': gathered_info.strip(),
            'iterations': iteration,
            'search_queries': search_queries,
            'completeness': final_eval,
            'thinking_steps': thinking_steps
        }


# Global loop thinking instance
_loopThinkingEngine: Optional[LoopThinkingEngine] = None


def getLoopThinkingEngine() -> LoopThinkingEngine:
    """Get or create global loop thinking engine instance."""
    global _loopThinkingEngine
    
    if _loopThinkingEngine is None:
        _loopThinkingEngine = LoopThinkingEngine(max_iterations=3, info_threshold=500)
    
    return _loopThinkingEngine
