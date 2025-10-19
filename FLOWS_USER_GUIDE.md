# Flows - Visual AI Workflow System

**Status**: ✅ Production Ready | **Version**: 1.0

---

## Overview

**Flows** is a visual workflow system that lets you create sophisticated AI pipelines by connecting nodes in a drag-and-drop interface. Chain multiple AI models, add conditional logic, loop over data, query knowledge bases, search the web, and more—all without writing code.

### Key Features

- 🎨 **Visual Editor** - Drag-and-drop interface with real-time previews
- 🤖 **9 Node Types** - Input, Model, Knowledge, Web Search, Transform, Conditional, Loop, Merge, Output
- 🔄 **Complex Workflows** - Branching, looping, and parallel processing
- 📊 **Execution History** - Track runs, view results, analyze performance
- 💾 **Import/Export** - Share workflows as JSON files
- 🔐 **Secure** - User-owned flows with authentication

---

## Quick Start

### 1. Access Flows

Navigate to **Workspace → Flows** in the sidebar menu.

### 2. Create Your First Flow

1. Click **"Create Flow"** button
2. Give your flow a name
3. Click **"Show Nodes"** to open the node library
4. Add nodes by clicking them in the library

### 3. Connect Nodes

Drag from a node's **output handle** (right side) to another node's **input handle** (left side).

### 4. Configure Nodes

Click any node to open its configuration panel on the right. Configure settings like:
- Model selection and prompts
- Transform operations
- Conditional logic
- Loop parameters

### 5. Save and Run

- Click **"Save"** to persist your flow
- Click **"Run Flow"** to execute
- Watch nodes change color as they execute (blue → green/red)
- View results in Output nodes

---

## Node Types Reference

### 📥 Input Node
**Purpose**: Capture user input to start the flow

**Features**:
- Text input with placeholder
- Media file selection (images, videos, audio)
- Default values

**Usage**:
```
Input → Model → Output
```

---

### 🤖 Model Node
**Purpose**: Execute AI models with custom prompts

**Features**:
- Select from all available models
- Prompt templates with variable interpolation
- Advanced settings (temperature, max tokens)
- Vision model support (images/videos)
- Streaming responses

**Variable Syntax**:
- `{{input}}` - Reference previous node output
- `{{node_id.output}}` - Reference specific node by ID
- `{{loop.output.value}}` - Access loop iteration data

**Example Prompt**:
```
Analyze this text and provide a summary: {{input}}
```

---

### 📚 Knowledge Node
**Purpose**: Query knowledge bases using RAG (Retrieval Augmented Generation)

**Features**:
- Select from your knowledge bases
- Configurable Top-K results (1-20)
- Confidence threshold filtering
- Reranking for better relevance
- Hybrid search (semantic + keyword)
- Include source metadata

**Usage**:
```
Input → Knowledge (retrieve context) → Model (answer with context) → Output
```

**Example**:
- Query: `{{input}}`
- Top-K: 5
- Returns relevant document chunks

---

### 🌐 Web Search Node
**Purpose**: Search the internet or scrape web pages

**Two Modes**:
1. **Search Mode**: Enter search query → Get search results
2. **URL Mode**: Enter URL → Scrape page content

**Features**:
- Auto-detect search vs URL
- Configurable max results (1-20)
- Returns structured data:
  - `title` - Page title
  - `url` - Source URL
  - `content` - Full page text
  - `snippet` - Preview (200 chars)

**Usage**:
```
Input → Web Search (query) → Loop (each result) → Web Search (fetch URL) → Model (analyze)
```

**Pro Tip**: Combine with Loop node to process multiple URLs

---

### 🔄 Transform Node
**Purpose**: Modify and manipulate text data

**6 Operations**:
1. **Uppercase** - Convert to UPPERCASE
2. **Lowercase** - Convert to lowercase
3. **Trim** - Remove whitespace
4. **Replace** - Find & replace with regex
5. **Extract** - Extract JSON field by name
6. **Template** - Apply template with `{{input}}`

**Example** (Extract JSON):
- Input: `{"name": "Alice", "age": 30}`
- Operation: Extract
- Field: `name`
- Output: `Alice`

---

### 🔀 Conditional Node
**Purpose**: Branch workflow based on conditions

**6 Operators**:
- **Equals** - Exact match
- **Not Equals** - Doesn't match
- **Contains** - Contains substring
- **Greater** - Numeric comparison (>)
- **Less** - Numeric comparison (<)
- **Regex** - Regular expression match

**Output Handles**:
- **TRUE** - Executes if condition met
- **FALSE** - Executes if condition not met

**Example**:
```
Input → Model → Conditional (sentiment == "positive") 
                   ├─ TRUE → Output "Positive response"
                   └─ FALSE → Output "Negative response"
```

---

### 🔁 Loop Node
**Purpose**: Iterate over data or repeat operations

**3 Loop Types**:

1. **Count Loop** - Simple N iterations
   - Config: Max iterations (e.g., 5)
   - Use case: Repeat refinement

2. **Array Loop** - Iterate over array elements
   - Config: Array path (e.g., `{{websearch.output.results}}`)
   - Use case: Process each search result

3. **Until Loop** - Loop until condition met
   - Config: Max iterations + break condition
   - Use case: Iterative improvement

**Output Handles**:
- **EACH** - Executes PER iteration (gets `{iteration, value}`)
- **DONE** - Executes ONCE after all iterations (gets aggregated results)

**Example** (Array Loop):
```
Web Search → Loop (EACH: loop over results)
              ├─ EACH → Transform (extract URL) → Web Search (fetch content)
              └─ DONE → Merge (all content) → Output
```

---

### 🔗 Merge Node
**Purpose**: Combine multiple inputs into one

**4 Strategies**:
1. **Concat** - Join as strings (with separator)
2. **Array** - Combine as array
3. **First** - Take only first input
4. **Last** - Take only last input

**Example**:
```
[Knowledge A, Knowledge B, Knowledge C] → Merge (concat with "\n\n") → Model → Output
```

---

### 📤 Output Node
**Purpose**: Display final results

**4 Formats**:
1. **Text** - Plain text display
2. **JSON** - Structured data (pretty-printed)
3. **Markdown** - Formatted text rendering
4. **File** - Media output (images, videos)

**Features**:
- Real-time result updates
- Accumulates results from loop iterations
- Copy to clipboard
- Download files

---

## Example Workflows

### Example 1: Simple Q&A with RAG
```
Input (question)
  → Knowledge (query docs, Top-K: 5)
  → Model (answer using context: "{{input}}")
  → Output (markdown)
```

**Use Case**: Ask questions about your documents

---

### Example 2: Multi-Source Research
```
Input (topic)
  → Web Search (search topic)
  → Loop (array: {{websearch.output.results}}, EACH)
     → Web Search (URL mode: {{loop.output.value.url}})
     → Transform (extract key info)
  → Loop (DONE)
  → Merge (concat all content)
  → Model (synthesize findings)
  → Output (markdown report)
```

**Use Case**: Comprehensive web research on any topic

---

### Example 3: Content Review Pipeline
```
Input (draft article)
  → Model A (Grammar check)
  → Model B (Fact check)
  → Model C (Style review)
  → Merge (concat all feedback)
  → Model D (Final revision based on feedback)
  → Output (improved article)
```

**Use Case**: Multi-stage content improvement

---

### Example 4: Conditional Processing
```
Input (customer message)
  → Model (classify sentiment)
  → Conditional (sentiment == "negative")
     ├─ TRUE → Model (empathetic response) → Output
     └─ FALSE → Model (standard response) → Output
```

**Use Case**: Customer service automation

---

### Example 5: Iterative Refinement
```
Input (initial draft)
  → Loop (count: 3, EACH)
     → Model (critique and improve)
     → Transform (extract improvements)
  → Loop (DONE)
  → Output (final polished version)
```

**Use Case**: Progressive content refinement

---

### Example 6: Vision + Research
```
Input (image)
  → Model (vision: describe image)
  → Web Search (search description)
  → Knowledge (query related docs)
  → Merge (web + knowledge context)
  → Model (comprehensive analysis)
  → Output
```

**Use Case**: Image analysis with contextual research

---

## Advanced Features

### Variable Interpolation

Use `{{variable}}` syntax to reference data:

**Simple reference**:
```
{{input}}  // Previous node's output
```

**Path navigation**:
```
{{websearch.output.results}}         // Get results array
{{loop.output.value.url}}            // Get URL from loop iteration
{{knowledge.output.chunks}}          // Get knowledge chunks
```

**In prompts**:
```
Analyze this: {{input}}

Based on these facts:
{{knowledge.output.chunks}}

Answer the question: {{input.query}}
```

---

### Execution History

Every flow execution is automatically saved with:

- ✅/❌ Status (success/error/aborted)
- ⏱️ Execution time (milliseconds)
- 📊 Node results (what each node produced)
- ⚠️ Errors (if any occurred)
- 📅 Timestamp

**View History**:
1. Open any flow
2. Click **"Execution History"** button
3. See statistics dashboard and execution list
4. Click any execution to view details

**Statistics Shown**:
- Total executions
- Success rate (%)
- Average execution time
- Last run timestamp

---

### Import/Export

**Export Flow**:
1. Open flow
2. Click **"Export"** button
3. Download JSON file

**Import Flow**:
1. Go to Flows list page
2. Click **"Import"** button
3. Select JSON file
4. Flow is created with new ID

**Use Cases**:
- Share workflows with team
- Backup important flows
- Version control (save to Git)
- Template distribution

---

## Tips & Best Practices

### 🎯 Design Tips

1. **Start Simple** - Test with basic flows first
2. **Use Descriptive Labels** - Rename nodes clearly (e.g., "Grammar Check Model")
3. **Test Incrementally** - Add nodes gradually, test often
4. **Check Output Nodes** - Always end with Output to see results
5. **Use Variables** - Leverage `{{node.output}}` for reusability

### ⚡ Performance Tips

1. **Limit Loop Iterations** - Set reasonable max iterations (avoid infinite loops)
2. **Optimize Prompts** - Shorter prompts = faster execution
3. **Use Top-K Wisely** - Knowledge/Search: More results = slower
4. **Stream When Possible** - Enable streaming for long responses

### 🐛 Debugging Tips

1. **Check Console** - Open browser console (F12) for detailed logs
2. **Color Coding** - Watch node colors during execution:
   - 🔵 Blue border = Running
   - 🟢 Green border = Success
   - 🔴 Red border = Error
3. **Test Paths** - Test TRUE/FALSE branches separately
4. **Simplify** - If flow fails, remove nodes until it works

### 🔒 Security Tips

1. **Review Prompts** - Ensure prompts don't leak sensitive data
2. **Validate Inputs** - Use Transform node to sanitize user input
3. **Limit Web Access** - Be cautious with Web Search on user input
4. **Knowledge Access** - Knowledge bases respect user permissions

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Save flow | Ctrl+S |
| Delete selected | Delete |
| Select all | Ctrl+A |
| Copy nodes | Ctrl+C |
| Paste nodes | Ctrl+V |
| Undo | Ctrl+Z |
| Redo | Ctrl+Y |

---

## Troubleshooting

### Flow Won't Execute

**Issue**: Nothing happens when clicking "Run Flow"

**Solutions**:
- ✅ Check browser console for errors
- ✅ Ensure at least one Input and Output node exists
- ✅ Verify all nodes are connected
- ✅ Check for circular dependencies (A → B → A)

---

### Node Shows Error

**Issue**: Node has red border after execution

**Solutions**:
- ✅ Click node to see error message in config panel
- ✅ Check if model is selected (Model nodes)
- ✅ Verify variable syntax (e.g., `{{input}}` not `{input}`)
- ✅ Ensure previous nodes succeeded

---

### Variables Not Working

**Issue**: `{{input}}` shows literally instead of substituting value

**Solutions**:
- ✅ Ensure node is connected (variables come from predecessors)
- ✅ Check spelling: `{{input}}` not `{{ input }}`
- ✅ For specific nodes: Use `{{node_id.output}}`
- ✅ Check execution order (predecessor must run first)

---

### Knowledge Node Returns No Results

**Issue**: Knowledge node finds nothing

**Solutions**:
- ✅ Verify knowledge base has documents
- ✅ Lower confidence threshold (set to 0 to see all results)
- ✅ Increase Top-K (try 10-20)
- ✅ Check query - try simpler/broader query
- ✅ Enable hybrid search for better matching

---

### Web Search Fails

**Issue**: Web Search node errors

**Solutions**:
- ✅ Check internet connectivity
- ✅ Verify search engine is configured in admin settings
- ✅ Try URL mode vs Search mode
- ✅ Reduce max results if timing out

---

### Loop Not Iterating

**Issue**: Loop only runs once or not at all

**Solutions**:
- ✅ Check loop type (count vs array)
- ✅ For array: Verify path points to actual array
- ✅ Check max iterations setting
- ✅ Ensure EACH handle is connected
- ✅ Look for errors in loop body nodes

---

## File Structure

For developers extending the system:

```
src/lib/
├── types/flows.ts                  # TypeScript type definitions
├── apis/flows/index.ts             # API client functions
├── stores/flows.ts                 # State management
└── components/flows/
    ├── FlowEditor.svelte           # Main visual editor
    ├── nodes/                      # Node components
    │   ├── InputNode.svelte
    │   ├── ModelNode.svelte
    │   ├── KnowledgeNode.svelte
    │   ├── WebSearchNode.svelte
    │   ├── TransformNode.svelte
    │   ├── ConditionalNode.svelte
    │   ├── LoopNode.svelte
    │   ├── MergeNode.svelte
    │   └── OutputNode.svelte
    ├── panels/                     # UI panels
    │   ├── NodeLibrary.svelte
    │   ├── NodeConfig.svelte
    │   └── ExecutionHistory.svelte
    └── execution/
        └── FlowExecutor.ts         # Execution engine

backend/open_webui/
├── models/flows.py                 # Database models
├── routers/flows.py                # API endpoints
└── migrations/versions/
    └── *_add_flow_table.py         # Database migrations
```

---

## API Reference

For programmatic access, see the backend API at `/api/v1/flows/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/flows/` | GET | List all user flows |
| `/api/v1/flows/create` | POST | Create new flow |
| `/api/v1/flows/{id}` | GET | Get specific flow |
| `/api/v1/flows/{id}` | POST | Update flow |
| `/api/v1/flows/{id}` | DELETE | Delete flow |
| `/api/v1/flows/{id}/duplicate` | POST | Duplicate flow |
| `/api/v1/flows/{id}/export` | GET | Export as JSON |
| `/api/v1/flows/import` | POST | Import from JSON |

All endpoints require authentication (Bearer token).

---

## Future Enhancements

See **FLOW_NODES_FEATURE_REVIEW.md** for the complete development roadmap.

**Coming Soon** (Phase 2B):
- 🔧 Tool/Function Node - Execute custom tools
- 🔄 Enhanced Transform - JSON/Array operations, custom JavaScript
- ⚡ Split/Fork Node - Parallel execution branches
- 🤖 Model Enhancements - Multi-model comparison, fallback chains

---

## Support

### Resources
- 📖 **Node Reference**: See "Node Types Reference" above
- 🗺️ **Development Roadmap**: `FLOW_NODES_FEATURE_REVIEW.md`
- 🐛 **Issues**: Check browser console (F12)
- 💬 **Community**: Open WebUI Discord/GitHub

### Getting Help

1. Check this guide's **Troubleshooting** section
2. Review **Example Workflows** for patterns
3. Open browser console for detailed error messages
4. Check execution history for past run details

---

**Version**: 1.0  
**Last Updated**: October 19, 2025  
**Status**: ✅ Production Ready with 9 node types

**Quick Links**:
- Development Roadmap: [FLOW_NODES_FEATURE_REVIEW.md](FLOW_NODES_FEATURE_REVIEW.md)
- Archived Docs: [docs/archive/](docs/archive/)
