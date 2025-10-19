# Web Search + Loop: Advanced Research Workflows

## Overview

The Web Search node now returns **structured arrays** that can be looped over, enabling powerful multi-stage research workflows.

## What Changed?

### Before:
```json
{
  "text": "Found 5 results..."
}
```

### Now:
```json
{
  "query": "AI trends 2024",
  "count": 5,
  "results": [
    {
      "title": "The Future of AI",
      "url": "https://example.com/article",
      "content": "Full article text...",
      "snippet": "AI is transforming...",
      "metadata": { /* additional data */ }
    },
    // ... more results
  ],
  "text": "Formatted summary..."
}
```

## Key Features

Each search result contains:
- **`title`** - Page/article title
- **`url`** - Source URL for deep diving
- **`content`** - Full extracted content
- **`snippet`** - 200-char preview
- **`metadata`** - Additional metadata (source, timestamps, etc.)

---

## Example Workflows

### 1. **Research & Summarize Multiple Sources** 📚

**What it does:** Search a topic, loop through results, summarize each, then merge.

**Flow:**
```
[Input: "quantum computing breakthroughs"]
    ↓
[Web Search (max 5 results)]
    ↓
[Loop (array: {{websearch_xxx.output.results}})]
    ├─ EACH → [Model: Summarize {{loop_xxx.output.value.content}}]
    └─ DONE → [Merge (concat)] → [Output]
```

**Setup:**
1. **Web Search Node**: Query = `{{input}}`, Max Results = 5
2. **Loop Node**: Type = `array`, Array Path = `{{websearch_xxx.output.results}}`
3. **Model Node** (connected to EACH):
   - Prompt: `Summarize this article in 2 sentences:\n\n{{loop_xxx.output.value.content}}`
4. **Merge Node** (collects all EACH outputs)
5. **Output Node**: Shows all summaries

**Result:** 5 concise summaries from different sources!

---

### 2. **Deep Research: Search → Filter → Analyze** 🔬

**What it does:** Search, filter relevant URLs, then deeply analyze each.

**Flow:**
```
[Input: "climate change policies"]
    ↓
[Web Search]
    ↓
[Loop over results]
    ├─ EACH → [Conditional: title contains "policy"?]
                ├─ TRUE → [Model: Analyze policy details]
                └─ FALSE → (skip)
    └─ DONE → [Output: Policy analysis]
```

**Setup:**
1. **Web Search**: Get initial results
2. **Loop**: Iterate over `{{websearch_xxx.output.results}}`
3. **Conditional** (EACH):
   - Condition: `{{loop_xxx.output.value.title}}`
   - Operator: `contains`
   - Compare To: `policy`
4. **Model** (TRUE branch): Deep analysis
5. **Output**: Only policy-related analyses

---

### 3. **URL Extraction & Secondary Search** 🔗

**What it does:** Search broad topic, extract URLs, then search each URL for specifics.

**Flow:**
```
[Input: "AI companies"]
    ↓
[Web Search: "top AI companies 2024"]
    ↓
[Loop over results]
    ├─ EACH → [Transform: Extract {{loop_xxx.output.value.url}}]
              ↓
              [Web Search: "{{url}} funding"]
              ↓
              [Model: Analyze funding]
    └─ DONE → [Merge] → [Output: Funding report]
```

**This enables:**
- Search for company list
- For each company, do a secondary search about funding
- Compile comprehensive funding report

---

### 4. **Competitive Intelligence** 🎯

**What it does:** Search competitors, analyze each, compare.

**Flow:**
```
[Input: "competitors of OpenAI"]
    ↓
[Web Search]
    ↓
[Loop]
    ├─ EACH → [Model: Extract company name from {{value.title}}]
              ↓
              [Web Search: "{{company_name}} latest news"]
              ↓
              [Model: Summarize news]
    └─ DONE → [Merge] → [Model: Compare all] → [Output]
```

**Result:** Comprehensive competitive analysis from multiple sources!

---

### 5. **Academic Research Assistant** 🎓

**What it does:** Search papers, extract key findings, build bibliography.

**Flow:**
```
[Input: "transformer architecture papers"]
    ↓
[Web Search (max 10)]
    ↓
[Loop]
    ├─ EACH → [Model: Extract key findings]
              ↓
              [Transform: Format as citation]
    └─ DONE → [Merge] → [Output: Annotated bibliography]
```

**Model Prompt for EACH:**
```
From this paper:
Title: {{loop_xxx.output.value.title}}
URL: {{loop_xxx.output.value.url}}
Content: {{loop_xxx.output.value.content}}

Extract:
1. Key finding
2. Methodology
3. Citation
```

---

## Accessing Loop Items

When looping over web search results, use:

```javascript
{{loop.output.value.title}}      // Current item's title
{{loop.output.value.url}}        // Current item's URL
{{loop.output.value.content}}    // Current item's content
{{loop.output.value.snippet}}    // Current item's snippet
{{loop.output.iteration}}        // Current iteration number (0-based)
```

**💡 Pro Tip:** You can use node **types** instead of full IDs!
- `{{websearch.output.results}}` instead of `{{websearch_1760870928991_abc.output.results}}`
- `{{loop.output.value}}` instead of `{{loop_1760870928991_xyz.output.value}}`
- `{{model.output}}` instead of `{{model_1760870928991_def.output}}`

This makes templates much cleaner and easier to maintain!

---

## Pro Tips

### Limit Processing
Use max results wisely - each loop iteration costs tokens:
- Research: 3-5 results
- Comprehensive: 10 results
- Quick check: 1-2 results

### Conditional Filtering
Add a conditional node after loop to only process relevant results:
```
Loop EACH → Conditional (relevance check) → Only process TRUE branch
```

### Parallel Processing (Future)
Currently loops run sequentially. For true parallel processing, use multiple web search nodes:
```
Input → Web Search 1 (query A) ┐
     → Web Search 2 (query B) ├─ Merge → Process
     → Web Search 3 (query C) ┘
```

### Error Handling
Some URLs may fail to scrape. The content will be empty but won't break the flow.

---

## Real-World Use Cases

1. **Investment Research**: Search company news → Loop → Analyze sentiment → Report
2. **Content Aggregation**: Search topic → Loop → Extract quotes → Compile article
3. **Due Diligence**: Search entity → Loop → Check each source → Risk assessment
4. **Academic Writing**: Search papers → Loop → Extract citations → Bibliography
5. **Market Research**: Search competitors → Loop → Compare features → Analysis
6. **News Monitoring**: Search keywords → Loop → Classify urgency → Alert
7. **Price Comparison**: Search products → Loop → Extract prices → Best deal

---

## Performance Notes

- Each web search creates a temporary collection
- Results are cached during flow execution
- Loop iterations are sequential (not parallel yet)
- Consider rate limits for API-based search engines

---

## Next Steps

Try building this simple example:

```
1. Input: "best programming languages 2024"
2. Web Search (max 3)
3. Loop over results
4. Model (EACH): "Summarize in one sentence: {{loop_xxx.output.value.content}}"
5. Merge (concat, separator: "\n\n")
6. Output
```

**Time to build:** 2 minutes  
**Result:** 3 expert summaries from different sources!

---

## Future Enhancements

- [ ] URL content fetcher node (for deep scraping)
- [ ] Parallel loop execution
- [ ] Result caching across flows
- [ ] Advanced filtering/sorting
- [ ] Image/PDF extraction from URLs
