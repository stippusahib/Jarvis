# JARVIS Native ReAct Agent — Multi-step reasoning loop (Thought -> Action -> Observation)
"""
Native ReAct Agent.
Allows JARVIS to think, use tools, and observe results before giving a final answer.
"""

import re
import json
import logging
from typing import List, Dict, Any, Callable, Optional
from tools.base import ToolExecutor, build_tool_descriptions
from tools import get_all_tools
from loop_guard import LoopGuard, LoopGuardConfig

# Will be integrated with LoopGuard (Phase 5) and Engine (Phase 6)
# For now, we keep it decoupled.

REACT_SYSTEM_PROMPT = """You are JARVIS, a capable desktop assistant.
You operate using a Thought-Action-Observation loop. For each step, you must respond with EXACTLY ONE of the following two formats:

Format 1: To think and use a tool
Thought: <your reasoning about what to do next>
Action: <tool_name>
Action Input: <json arguments for the tool>

Format 2: To give a final answer to the user
Thought: <your reasoning for the final answer>
Final Answer: <your conversational response>

CRITICAL RULES:
1. Always start with "Thought: ".
2. If you use Format 1, you MUST provide "Action:" and "Action Input:". The Action Input must be valid JSON.
3. If you use Format 2, you MUST provide "Final Answer:".
4. Do not output both an Action and a Final Answer in the same step.
5. If a tool fails, think about why it failed and either try a different approach or give a Final Answer explaining the problem.

{tool_descriptions}"""


class ReActAgent:
    """Thought -> Action -> Observation loop agent."""

    def __init__(self, llm_generate_fn: Callable[[List[Dict[str, str]]], str]):
        """
        Initialize the ReAct agent.
        
        Args:
            llm_generate_fn: A function that takes a list of message dicts (role/content) 
                             and returns the LLM's string response.
        """
        self.executor = ToolExecutor(get_all_tools())
        self.llm_generate = llm_generate_fn
        self.max_turns = 10  # Increased for ReAct loops
        self.tool_descriptions = build_tool_descriptions(self.executor.tool_list)
        self.loop_guard = LoopGuard()

    def _parse_response(self, text: str) -> dict:
        """Parse ReAct structured output."""
        result = {"thought": "", "action": "", "action_input": "", "final_answer": ""}

        # Extract Thought
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=\nAction:|\nFinal Answer:|\Z)",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if thought_match:
            result["thought"] = thought_match.group(1).strip()

        # Extract Action & Action Input
        action_match = re.search(r"Action:\s*([^\n]+)", text, re.IGNORECASE)
        if action_match:
            result["action"] = action_match.group(1).strip()
            
            input_match = re.search(
                r"Action Input:\s*(.+?)(?=\nObservation:|\nThought:|\nFinal Answer:|\Z)",
                text,
                re.DOTALL | re.IGNORECASE,
            )
            if input_match:
                # Clean up markdown JSON blocks
                raw_input = input_match.group(1).strip()
                if raw_input.startswith("```json"):
                    raw_input = raw_input[7:]
                if raw_input.startswith("```"):
                    raw_input = raw_input[3:]
                if raw_input.endswith("```"):
                    raw_input = raw_input[:-3]
                result["action_input"] = raw_input.strip()

        # Extract Final Answer
        final_match = re.search(
            r"Final Answer:\s*(.+?)\Z", text, re.DOTALL | re.IGNORECASE
        )
        if final_match:
            result["final_answer"] = final_match.group(1).strip()

        return result

    def run(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Run the ReAct loop for a user query.
        """
        messages = []
        
        # 1. Add System Prompt
        sys_prompt = REACT_SYSTEM_PROMPT.format(tool_descriptions=self.tool_descriptions)
        messages.append({"role": "system", "content": sys_prompt})
        
        # 2. Add history (if any)
        if conversation_history:
            messages.extend(conversation_history)
            
        # 3. Add current user input
        messages.append({"role": "user", "content": user_input})
        
        # 4. Agent Loop
        self.loop_guard.reset()
        
        for step in range(self.max_turns):
            # Compress context if needed to avoid token overflow
            messages = self.loop_guard.compress_context(messages)
            
            # Call LLM
            try:
                response_text = self.llm_generate(messages)
            except Exception as e:
                return f"Brain connection lost during reasoning: {e}"
                
            # Log the raw response for debugging
            logging.debug(f"[ReAct Step {step+1}] LLM Response:\n{response_text}")
            
            # Append assistant response to history
            messages.append({"role": "assistant", "content": response_text})
            
            # Parse structure
            parsed = self._parse_response(response_text)
            
            # Check for Final Answer
            if parsed.get("final_answer"):
                return parsed["final_answer"]
                
            # Check for Action
            action = parsed.get("action")
            action_input_str = parsed.get("action_input")
            
            if action and action_input_str:
                # Attempt to parse JSON input
                try:
                    action_args = json.loads(action_input_str)
                except json.JSONDecodeError:
                    # If JSON fails, pass it as a raw string under a default key
                    # Or tell the LLM it messed up the JSON
                    observation = "Error: Action Input must be valid JSON."
                    messages.append({"role": "user", "content": f"Observation: {observation}"})
                    continue
                    
                # Loop Guard Check
                verdict = self.loop_guard.check_call(action, action_args)
                if verdict.blocked:
                    logging.warning(verdict.reason)
                    messages.append({"role": "user", "content": f"Observation: {verdict.reason}"})
                    continue
                    
                # Execute tool
                logging.info(f"Executing tool: {action} with args: {action_args}")
                tool_result = self.executor.execute(action, action_args)
                
                # Append Observation
                observation = tool_result.content
                if not tool_result.success:
                    observation = f"Tool Failed: {observation}"
                    
                messages.append({"role": "user", "content": f"Observation: {observation}"})
                
            elif not action and not parsed.get("final_answer"):
                # LLM didn't output Action or Final Answer
                observation = "Error: You must provide either an 'Action' or a 'Final Answer'."
                messages.append({"role": "user", "content": f"Observation: {observation}"})
                
        # If we exit the loop without a final answer
        return "I tried to solve this, but I reached my thinking limit. Please try rephrasing your request."

