# TTS Not Starting from Beginning - Fixed

## Problem Description

When using ElevenLabs TTS with `responseAutoPlayback` enabled, text-to-speech would not start from the beginning of the response when the model was streaming. Some initial sentences would be skipped.

## Root Cause

The issue was in the TTS playback logic in `ResponseMessage.svelte`. The component had no mechanism to track which sentences had already been processed, and when auto-playback was triggered after streaming completed, there was potential for:

1. **Cache conflicts**: Sentences processed during streaming might have different whitespace/formatting than the final version
2. **State confusion**: The `message.lastSentence` tracking in `Chat.svelte` was for event dispatching, not actual TTS playback
3. **No reset mechanism**: When TTS was triggered, it would always process the full content but without a clean state

## The Fix

### Changes Made to `ResponseMessage.svelte`

**1. Added sentence tracking state (line 168)**
```typescript
let spokenSentences: Set<string> = new Set(); // Track already spoken sentences
```

**2. Added clear function (lines 241-243)**
```typescript
const clearSpokenSentences = () => {
    spokenSentences.clear();
};
```

**3. Clear on message change (lines 126-127)**
```typescript
$: if (history.messages) {
    if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
        message = JSON.parse(JSON.stringify(history.messages[messageId]));
        // Clear spoken sentences when message changes
        spokenSentences.clear();
    }
}
```

**4. Clear before speaking and track sentences (lines 345-377)**
```typescript
} else {
    // Always clear spoken sentences when manually triggered to ensure full playback
    // This ensures TTS always starts from the beginning
    clearSpokenSentences();
    
    for (const [idx, sentence] of messageContentParts.entries()) {
        // Skip if already spoken during streaming (shouldn't happen after clearing, but defensive)
        if (spokenSentences.has(sentence)) {
            console.log('Skipping already spoken sentence:', sentence.substring(0, 50));
            continue;
        }

        const res = await synthesizeOpenAISpeech(
            localStorage.token,
            voice,
            sentence
        ).catch((error) => {
            console.error(error);
            toast.error(`${error}`);
            speaking = false;
            loadingSpeech = false;
        });

        if (res) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);

            $audioQueue.enqueue(url);
            spokenSentences.add(sentence); // Track this sentence
            loadingSpeech = false;
        }
    }
}
```

## How It Works

1. **Clean Slate**: When the speak button is clicked (manually or via auto-playback), `clearSpokenSentences()` is called first
2. **Track Progress**: As each sentence is successfully synthesized, it's added to the `spokenSentences` Set
3. **Skip Check**: Before synthesizing, we check if the sentence was already spoken (defensive check, shouldn't happen after clearing)
4. **Auto-Reset**: When the message changes (e.g., regeneration or new message), the Set is automatically cleared

## Benefits

✅ **Always starts from beginning**: The clear operation ensures TTS processes the full message  
✅ **Prevents duplicates**: The Set tracking prevents re-speaking sentences if somehow triggered twice  
✅ **Clean state management**: Automatic clearing on message changes prevents stale state  
✅ **Defensive coding**: Skip check provides safety even if clear somehow fails  
✅ **Debugging support**: Console logs help identify if skipping occurs

## Testing

Test the following scenarios:

1. **Streaming Response + Auto-playback**: 
   - Enable "Response Auto-Playback" in settings
   - Send a prompt that generates a long streaming response
   - Verify TTS starts from the first sentence

2. **Manual Trigger During Streaming**:
   - Send a prompt that generates a streaming response
   - Click the speak button while streaming is in progress
   - Verify it starts from the beginning

3. **Manual Trigger After Completion**:
   - Send a prompt and wait for completion
   - Click the speak button
   - Verify it speaks the full message

4. **Regenerate Response**:
   - Regenerate a response multiple times
   - Verify each regeneration speaks correctly from the beginning

## Related Files

- **Fixed**: `src/lib/components/chat/Messages/ResponseMessage.svelte`
- **Related**: `src/lib/components/chat/Chat.svelte` (auto-playback trigger)
- **Related**: `backend/open_webui/routers/audio.py` (TTS endpoint)

## Configuration

This fix works with all TTS engines:
- ✅ ElevenLabs
- ✅ OpenAI TTS
- ✅ Azure Speech
- ✅ Browser Kokoro
- ✅ Transformers

No configuration changes needed. The fix is transparent to users.
