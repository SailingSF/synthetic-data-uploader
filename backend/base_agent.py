from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import logging
from typing import Optional, Dict, Any, List

load_dotenv()
logger = logging.getLogger(__name__)

class OpenAIAgent:
    def __init__(
        self,
        instructions: str,
        tools_map: Optional[Dict[str, callable]] = None,
        structured_output: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tool_retries: int = 3
    ):
        """Initialize an OpenAI Agent with tools and conversation capabilities.
        
        Args:
            instructions: System prompt/instructions for the agent
            tools_map: Dictionary mapping tool names to their implementation functions
            structured_output: If set, ensures response is valid JSON matching this schema
            model: OpenAI model to use (must support tool calls if tools are provided)
            max_tool_retries: Maximum number of times to retry tool calls (default: 3)
        """
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.instructions = instructions
        self.tools_map = tools_map or {}
        self.structured_output = structured_output
        # Set role based on model name
        role = "developer" if model.startswith("o") else "system"
        self.messages = [{"role": role, "content": instructions}]
        self.max_tool_retries = max_tool_retries
        
        # Convert tools_map to OpenAI tools format if tools are provided
        self.tools_list = None
        if self.tools_map:
            self.tools_list = [
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        # Preserve any existing function metadata if available
                        **(getattr(func, "__openai_schema__", {"parameters": {}}) 
                           if hasattr(func, "__openai_schema__") else {"parameters": {}})
                    }
                }
                for name, func in self.tools_map.items()
            ]
    
    def add_message(self, message, role: str = None):
        """
        Add a message to the conversation history.
        message can be either a string or a dict with role and content
        """
        if isinstance(message, dict):
            self.messages.append(message)
        else:
            if not role:
                role = "user"
            self.messages.append({
                "role": role,
                "content": str(message)  # Ensure content is string
            })

    def run_thread(self, tool_choice: str = "auto"):
        if self.tools_list:
            completion = self._get_completion(tool_choice = tool_choice)
        else:
            completion = self._get_completion()

        retry_count = 0
        tool_calls = completion.choices[0].message.tool_calls
        
        while tool_calls:
            if retry_count >= self.max_tool_retries:
                logger.error(f"Max tool retries ({self.max_tool_retries}) reached")
                error_msg = "I apologize, but I'm having trouble processing some data. Could you please rephrase your request?"
                self.messages.append({"role": "assistant", "content": error_msg})
                return error_msg
                
            self.messages.append(completion.choices[0].message)
            had_error = False
            
            for tool_call in tool_calls:
                try:
                    function_name = tool_call.function.name
                    if function_name not in self.tools_map:
                        raise ValueError(f"Unknown function: {function_name}")
                        
                    function_args = json.loads(tool_call.function.arguments)
                    function_response = self.tools_map[function_name](**function_args)
                    function_response_json = json.dumps(function_response)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON arguments for tool {function_name}: {e}")
                    had_error = True
                    function_response_json = json.dumps({
                        "error": f"Invalid arguments format: {str(e)}"
                    })
                except TypeError as e:
                    logger.error(f"Invalid arguments for tool {function_name}: {e}")
                    had_error = True
                    function_response_json = json.dumps({
                        "error": f"Invalid arguments: {str(e)}"
                    })
                except Exception as e:
                    logger.error(f"Error executing tool {function_name}: {e}", exc_info=True)
                    had_error = True
                    function_response_json = json.dumps({
                        "error": f"Tool execution failed: {str(e)}"
                    })
                
                self.messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response_json,
                })
            
            if had_error:
                retry_count += 1
                logger.info(f"Tool call error, retry {retry_count}/{self.max_tool_retries}")
            
            completion = self._get_completion()
            tool_calls = completion.choices[0].message.tool_calls
        
        self.messages.append(completion.choices[0].message)
        return completion.choices[0].message.content

    def run_message(self, prompt: str):
        self.add_message(prompt)
        response = self.run_thread()
        
        # If we're expecting a JSON response, parse it
        if self.structured_output and isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise
        
        return response
        
    def _get_completion(self, tool_choice: str = 'auto'):
        kwargs = {
            "model": self.model,
            "messages": self.messages,
        }
        
        # Only add tools-related parameters if tools are present
        if self.tools_list:
            kwargs["tools"] = self.tools_list
            kwargs["tool_choice"] = tool_choice
        
        # Add response format if structured output is requested
        if self.structured_output:
            kwargs["response_format"] = {"type": "json_object"}
        
        completion = self.client.chat.completions.create(**kwargs)
        return completion 