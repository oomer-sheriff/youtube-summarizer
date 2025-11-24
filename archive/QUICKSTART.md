# 🚀 Quick Start Guide

## Get Started in 3 Minutes

### Step 1: Install Dependencies

```bash
cd youtube_summarizer/backend
pip install -r requirements.txt
```

⏱️ *This may take 5-10 minutes on first install*

### Step 2: Start the Server

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 3: Try It Out!

#### Option A: Interactive Demo (Recommended)

Open a new terminal and run:
```bash
python interactive_demo.py
```

Then just paste a YouTube URL and chat!

#### Option B: Direct API Call

```bash
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize this video: https://youtube.com/watch?v=dQw4w9WgXcQ"}'
```

#### Option C: Browser

Visit: `http://localhost:8000/docs`

This opens the interactive API documentation where you can test all endpoints!

## 🎯 Common Use Cases

### 1. Summarize a Video

**Interactive Demo:**
```
You: Can you summarize https://youtube.com/watch?v=VIDEO_ID
```

**API:**
```bash
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize https://youtube.com/watch?v=VIDEO_ID"}'
```

### 2. Ask Follow-up Questions

**Interactive Demo:**
```
You: What are the main points?
Assistant: The main points are...

You: Can you elaborate on the second point?
Assistant: Sure! The second point...
```

**API:**
```bash
# Save conversation_id from first response
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the main points?",
    "conversation_id": "YOUR_CONVERSATION_ID_HERE"
  }'
```

### 3. Get Video Transcript

**Interactive Demo:**
```
You: Can you get me the transcript of https://youtube.com/watch?v=VIDEO_ID
```

**API:**
```bash
curl -X POST http://localhost:8000/mcp/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Get transcript of https://youtube.com/watch?v=VIDEO_ID"}'
```

## 📱 Integration Examples

### Python Client

```python
import requests

def chat(message, conversation_id=None):
    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    
    response = requests.post(
        "http://localhost:8000/mcp/chat",
        json=payload
    )
    return response.json()

# Use it
result = chat("Summarize https://youtube.com/watch?v=VIDEO_ID")
print(result['response'])

# Follow-up
result = chat("What are the key points?", result['conversation_id'])
print(result['response'])
```

### JavaScript Client

```javascript
async function chat(message, conversationId = null) {
    const payload = { message };
    if (conversationId) {
        payload.conversation_id = conversationId;
    }
    
    const response = await fetch('http://localhost:8000/mcp/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    return await response.json();
}

// Use it
const result = await chat('Summarize https://youtube.com/watch?v=VIDEO_ID');
console.log(result.response);

// Follow-up
const result2 = await chat('What are the key points?', result.conversation_id);
console.log(result2.response);
```

## 🎓 Example Conversations

### Research Assistant
```
You: Summarize https://youtube.com/watch?v=AI_LECTURE_VIDEO
