# System Prompt Fix - Preventing Tool Refusals

## Problem Identified

The Arch-Function-1.5B model was:
1. ✅ Successfully detecting YouTube URLs
2. ✅ Calling the correct tools
3. ✅ Receiving tool results
4. ❌ **BUT** then refusing to use the results, saying "I can't access YouTube"

### Log Evidence

```
Line 777: "I'm sorry, but I can't access external websites..."  ❌
Line 782-790: LLM decided to call 3 tool(s)  ✅
Line 804: Tool 'search_transcript' returned result  ✅
Line 859: Getting final response with tool results...  ✅
Result: User still gets refusal message  ❌
```

## Root Cause

The model has safety training that makes it say "I cannot access external websites." Even though it was calling tools correctly, the **system prompt wasn't strong enough** to override this refusal behavior when generating the final response.

## Solution Applied

### Change 1: Stronger System Prompt

**Before:**
```python
TASK_PROMPT = """You are a YouTube video analysis assistant with special tools.

You HAVE ACCESS to these capabilities:
- get_video_info: Check video length and stats
- search_transcript: Search within video content
- get_video_transcript: Get full video transcripts

When user asks about a YouTube video URL, YOU MUST use these tools.
NEVER say you "can't access YouTube" - you can, via your tools."""
```

**After:**
```python
TASK_PROMPT = """You are an AI assistant with direct access to YouTube video analysis tools.

CRITICAL INSTRUCTIONS:
1. When you see a YouTube URL, YOU MUST use the available tools
2. You CAN access YouTube - you have special tools for this purpose
3. NEVER say "I can't access YouTube" or "I can't access external websites"
4. After receiving tool results, ALWAYS use them to answer the user's question
5. Tool results contain the actual video content - summarize and explain them to the user
6. If tools return empty results, mention that specifically instead of refusing

Available capabilities:
- get_video_info: Check video length, word count, and statistics
- search_transcript: Search for specific topics within the video
- get_video_transcript: Get the complete video transcript

YOU HAVE THESE TOOLS. USE THEM."""
```

**Key improvements:**
- Numbered instructions (more explicit)
- Explicit prohibition of refusal phrases
- **Instructions about using tool results** (this was missing!)
- More direct language ("YOU MUST", "YOU CAN")

### Change 2: Explicit Tool Result Usage Instructions

**Before:**
```python
FORMAT_PROMPT = """
For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
""".strip()
```

**After:**
```python
FORMAT_PROMPT = """
For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

IMPORTANT: After tools execute and return results, you will receive those results in <tool_response> tags.
You MUST use these tool results to answer the user's question. Do NOT ignore tool results.
Do NOT say you cannot access the content when you have just received it via tools.""".strip()
```

**Key addition:**
- Explicit instructions about what happens AFTER tool execution
- Prohibition against ignoring tool results
- Direct contradiction of refusal behavior

### Change 3: Clearer Tool Result Presentation

**Before:**
```python
tool_results_text = "\n".join([
    f"<tool_response>\n{json.dumps(result)}</tool_response>"
    for result in execution_results
])
```

**After:**
```python
tool_results_text = "TOOL RESULTS (use these to answer the user's question):\n\n"
tool_results_text += "\n".join([
    f"<tool_response>\n{json.dumps(result)}\n</tool_response>"
    for result in execution_results
])
```

**Key improvement:**
- Adds explicit prefix telling the model to use the results
- Makes it impossible for the model to miss that these are tool results

## Expected Behavior After Fix

### Before Fix:
```
User: "What is this video about? [URL]"
Model: [Calls tools] ✅
Model: [Gets results] ✅
Model: "I'm sorry, I can't access YouTube..." ❌
```

### After Fix:
```
User: "What is this video about? [URL]"
Model: [Calls tools] ✅
Model: [Gets results] ✅
Model: "Based on the video transcript, this video is about..." ✅
```

## Testing

To test the fix:

1. **Restart the intelligent proxy:**
   ```bash
   # Ctrl+C to stop current server
   python ollama_proxy_intelligent.py
   ```

2. **Ask a question about a YouTube video:**
   ```
   "What is this video about? https://www.youtube.com/shorts/Pw9uwXvLNdo"
   ```

3. **Expected behavior:**
   - Model should call tools (check logs)
   - Model should use tool results in response
   - Model should NOT say "I can't access YouTube"

## Logs to Watch

When it works correctly, you should see:

```
INFO - LLM decided to call X tool(s)
INFO - Executing FastMCP tool 'get_video_info'...
INFO - Tool 'get_video_info' returned result of length X
INFO - Getting final response with tool results...
```

And the response should **use the actual content** from the tools, not a refusal.

## Why This Works

The model has two competing behaviors:
1. **Safety training:** "Don't claim to access external websites"
2. **Tool following:** "Use tools when available"

By making the system prompt **extremely explicit** about:
- Having tools available
- MUST use tool results
- NOT refusing when tools provide data

We push the model's behavior strongly toward tool-following and away from refusal.

## Files Modified

- `ollama_proxy_intelligent.py` (lines 213-251, 358-363)

## Date

November 17, 2024

## Status

✅ **Applied and ready for testing**

---

**Note:** If the model still refuses occasionally, you can make the prompt even MORE explicit, or consider using temperature=0 for the initial tool-calling phase to make it more deterministic.

