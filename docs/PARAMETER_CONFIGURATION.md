# Parameter Configuration Guide

## Quick Reference

| Parameter | Range | Default | Effect |
|-----------|-------|---------|--------|
| **n_iterations** | 1-5 | 3 | How many search loops to run |
| **max_results** | 1-10 | 3 | Search results processed per loop |
| **info_threshold** | 100-2000 | 500 | Min chars before stopping loops |

## Detailed Parameter Explanations

### 1. n_iterations (Number of Iterations)

**Definition:** How many times the thinking loop attempts to gather information.

**Range:** 1 to 5

**Default:** 3

**Unit:** Number of loops/iterations

#### How It Works

The thinking system works iteratively:
1. **Iteration 1:** Initial query, gets first search results
2. **Iteration 2:** Refined query, gets more specific results
3. **Iteration 3:** Further refinement, gathers more comprehensive info
4. **Iterations 4-5:** Deep research, very thorough investigation

#### Impact on Behavior

**Value: 1**
- Single search attempt
- Fastest response (1-2 seconds)
- May miss important information
- Best for: Simple factual queries
- Example: "What is Python?"

**Value: 2**
- Two search attempts with refinement
- Moderate response time (2-4 seconds)
- Good balance of speed and quality
- Best for: General questions
- Example: "How to learn Python?"

**Value: 3 (Default)**
- Three iterations with progressive refinement
- Good response time (3-6 seconds)
- Comprehensive without excessive searching
- Best for: Most questions
- Recommended general setting

**Value: 4**
- Four search attempts with deep refinement
- Longer response time (5-8 seconds)
- Very thorough investigation
- Best for: Complex or nuanced queries
- Example: "Compare Python vs JavaScript for web development"

**Value: 5**
- Five iterations, maximum depth
- Longest response time (8-15 seconds)
- Extremely comprehensive research
- Best for: Research questions
- Example: "History and evolution of artificial intelligence"

#### Performance Impact

```
Iterations vs Response Time (approximate):
1 iteration:  ~1-2 seconds
2 iterations: ~2-4 seconds
3 iterations: ~3-6 seconds (default)
4 iterations: ~5-8 seconds
5 iterations: ~8-15 seconds
```

#### When To Adjust

**Increase (3→4-5) when:**
- You need comprehensive, well-researched answers
- The topic is complex or requires deep understanding
- You have time for longer responses
- You want maximum information gathering

**Decrease (3→1-2) when:**
- You need quick responses
- The query is straightforward
- You're on a slow connection
- You want to save processing resources

#### Recommended Settings by Use Case

- **Quick facts:** 1-2 iterations
- **General Q&A:** 3 iterations (default)
- **Research:** 4-5 iterations
- **Emergency lookup:** 1 iteration

---

### 2. max_results (Maximum Search Results)

**Definition:** How many search results to process and analyze per iteration.

**Range:** 1 to 10

**Default:** 3

**Unit:** Number of results per search query

#### How It Works

For each iteration, the system:
1. Performs a web search
2. Gets up to 10 results from search engine
3. Selects top `max_results` entries
4. Extracts and analyzes content
5. Accumulates information

#### Impact on Behavior

**Value: 1**
- Processes only the top result
- Fastest analysis (minimal content reading)
- May be too narrow
- Best for: Time-critical queries
- Example: "Current Bitcoin price"

**Value: 2**
- Processes top 2 results
- Fast but more comprehensive
- Good for: Simple facts with multiple sources
- Example: "Capital of France"

**Value: 3 (Default)**
- Balanced approach
- Processes top 3 results
- Good coverage without excessive reading
- Recommended general setting
- Best for: Most questions

**Value: 5**
- Processes 5 results
- More comprehensive coverage
- Longer analysis time (1-2 extra seconds)
- Multiple perspectives captured
- Best for: Questions needing multiple viewpoints
- Example: "Pros and cons of cryptocurrency"

**Value: 8-10**
- Maximum comprehensive analysis
- Processes many results
- Significantly longer processing time (3-5 extra seconds)
- Very thorough information gathering
- Best for: In-depth research queries
- Example: "Complete analysis of climate change impacts"

#### Performance Impact

```
Max Results vs Processing Time (per iteration):
1 result:   ~0.5-1 second
2 results:  ~1-2 seconds
3 results:  ~1.5-2.5 seconds (default)
5 results:  ~2.5-4 seconds
8 results:  ~4-6 seconds
10 results: ~5-7 seconds
```

#### When To Adjust

**Increase (3→5-10) when:**
- You want diverse perspectives
- Question benefits from multiple sources
- You need comprehensive coverage
- Time is not a constraint

**Decrease (3→1-2) when:**
- You need quick results
- A single authoritative source is sufficient
- Processing speed is critical
- You want to minimize information

#### Recommended Settings by Use Case

- **Quick lookup:** 1-2 results
- **General queries:** 3 results (default)
- **Comparative analysis:** 5-8 results
- **Deep research:** 8-10 results

---

### 3. info_length_threshold (Information Length Threshold)

**Definition:** Minimum amount of character data needed before the system stops gathering information.

**Range:** 100 to 2000 characters

**Default:** 500 characters

**Unit:** Character count

#### How It Works

The system:
1. Gathers information from web search results
2. Tracks total character count accumulated
3. Continues iterations until meeting threshold
4. Stops early if all iterations exhausted

```
Information Accumulation Example:
Iteration 1: 120 chars collected (need 500, continue...)
Iteration 2: 240 chars collected (need 500, continue...)
Iteration 3: 580 chars collected (≥500, STOP! enough info)
```

#### Impact on Behavior

**Value: 100**
- Stops gathering very quickly
- Minimum 100 characters of info
- Fastest responses (1-2 seconds)
- Limited but quick information
- Best for: Facts/brief answers
- Example: "When was Python released?" → "1991" (enough)

**Value: 300**
- Stops after modest information gathering
- Brief but somewhat detailed
- Fast responses (2-3 seconds)
- Good for: Quick summaries
- Example: "Benefits of exercise" → brief list (enough)

**Value: 500 (Default)**
- Balanced information gathering
- Moderate detail level
- Good response time (3-6 seconds)
- Sufficient for most questions
- Recommended general setting

**Value: 800**
- Significant information requirement
- Detailed responses
- Longer processing time (5-8 seconds)
- Good for: Complex topics needing detail
- Example: "Machine learning algorithms" → comprehensive overview

**Value: 1200**
- Extensive information gathering
- Very detailed responses
- Significant processing time (7-10 seconds)
- For: In-depth explorations
- Example: "History of internet" → detailed timeline

**Value: 2000**
- Maximum information gathering
- Very comprehensive responses
- Longest processing time (10-15 seconds)
- For: Research requiring maximum detail
- Example: "Climate change science explained" → very thorough

#### Performance Impact

```
Info Threshold vs Information Quality:
100 chars:   Brief, may be incomplete
300 chars:   Summary level detail
500 chars:   Balanced, good detail (default)
800 chars:   Substantial detail
1200 chars:  Extensive detail
2000 chars:  Maximum comprehensive detail
```

#### Content Size Reference

What fits in different thresholds:

**100 characters:**
```
"Python is a high-level programming language created in 1991. 
It emphasizes code readability."
```

**300 characters:**
```
"Python is a high-level programming language. Benefits: Easy to learn, 
readable syntax, large community. Used for: Web development, data analysis, 
AI, automation. First release: 1991 by Guido van Rossum."
```

**500 characters (Default):**
```
"Python is a high-level, interpreted programming language emphasizing 
code readability. Created by Guido van Rossum in 1991. Key benefits: 
Easy to learn, readable syntax, extensive libraries, large community. 
Used in web development (Django), data analysis (NumPy, Pandas), 
artificial intelligence (TensorFlow), automation, and scientific computing."
```

#### When To Adjust

**Increase (500→800-2000) when:**
- You want very detailed, comprehensive answers
- The topic is complex and needs thorough explanation
- You have time for longer processing
- You want maximum context and background

**Decrease (500→100-300) when:**
- You need quick answers
- Brief summaries are sufficient
- You're interested in quick facts only
- Processing speed is more important than detail

#### Recommended Settings by Use Case

- **Quick facts only:** 100-200 characters
- **Brief summaries:** 200-400 characters
- **Balanced detail:** 500 characters (default)
- **Substantial information:** 800-1000 characters
- **Comprehensive research:** 1200-2000 characters

---

## Configuration Combinations

### Presets for Common Use Cases

#### Fast Mode - Quick Answers
```
n_iterations: 1
max_results: 2
info_threshold: 200
Response time: ~1-2 seconds
Use case: Quick fact lookup
Example: "What's the population of NYC?"
```

#### Balanced Mode - Recommended Default
```
n_iterations: 3
max_results: 3
info_threshold: 500
Response time: ~3-6 seconds
Use case: General questions
Example: "How do photosynthesis work?"
```

#### Thorough Mode - Detailed Answers
```
n_iterations: 4
max_results: 6
info_threshold: 900
Response time: ~6-10 seconds
Use case: Complex questions
Example: "Explain quantum computing"
```

#### Research Mode - Maximum Depth
```
n_iterations: 5
max_results: 10
info_threshold: 1500
Response time: ~10-15 seconds
Use case: In-depth research
Example: "Comprehensive overview of climate change"
```

#### Economy Mode - Minimal Resources
```
n_iterations: 1
max_results: 1
info_threshold: 100
Response time: <1 second
Use case: Simple facts only
Example: "Abbreviation: AI"
```

---

## Interaction Between Parameters

### How Parameters Affect Total Processing Time

**Formula (Approximate):**
```
Total Time = (n_iterations × max_results × 1-2 seconds) 
           + overhead
```

**Examples:**
- 1 × 2 = ~1-2 seconds total
- 3 × 3 = ~3-6 seconds total (default)
- 5 × 10 = ~10-15 seconds total

### Impact on Information Quality

**Better quality when:**
- Higher n_iterations (more search refinement)
- Higher max_results (more sources)
- Higher info_threshold (more comprehensive)

**Example: Research Query**
- Low iterations + low results + low threshold = Shallow answer
- High iterations + high results + high threshold = Deep answer

### Balancing Speed vs Quality

```
Speed Priority:           Quality Priority:
n_iterations: 1           n_iterations: 5
max_results: 1-2          max_results: 8-10
info_threshold: 100-200   info_threshold: 1000-2000
Result: ~1-2 sec          Result: ~10-15 sec
```

---

## Tuning Guide

### Step 1: Identify Your Priority
- **Speed:** Reduce all parameters
- **Quality:** Increase all parameters
- **Balanced:** Use defaults or adjust one at a time

### Step 2: Start from Preset
- Choose closest matching preset above
- Or start with Balanced Mode (defaults)

### Step 3: Fine-Tune Individual Parameters

**If answers are too brief:**
- Increase `info_threshold` by 200-300 chars
- Or increase `max_results` by 2-3
- Or increase `n_iterations` by 1

**If processing is too slow:**
- Decrease `n_iterations` by 1-2
- Or decrease `max_results` by 2-3
- Or decrease `info_threshold` by 200-300 chars

**If answers lack multiple perspectives:**
- Increase `max_results` to 5-8

**If answers lack depth/refinement:**
- Increase `n_iterations` to 4-5

### Step 4: Test and Observe
Send a test query and observe:
- Response time: Is it acceptable?
- Answer quality: Enough detail?
- Answer diversity: Multiple sources?

### Step 5: Iterate
Adjust one parameter at a time and test until satisfied.

---

## Monitoring Configuration Effects

### Indicators to Watch

**Information Quality:**
- Number of sources cited
- Depth of explanation
- Presence of examples/context
- Multiple perspectives covered

**Processing Efficiency:**
- Response generation time
- Web search rounds completed
- Content processing speed
- System resource usage

**Balance Assessment:**
- Too fast but shallow? → Increase thresholds
- Too slow but not helpful? → Decrease iterations
- Just right? → Keep current settings

---

## Troubleshooting Configuration Issues

### Problem: Responses Too Brief
**Solution Options:**
1. Increase `info_threshold` to 800-1000
2. Increase `max_results` to 5-8
3. Increase `n_iterations` to 4-5

### Problem: Processing Too Slow
**Solution Options:**
1. Decrease `n_iterations` to 1-2
2. Decrease `max_results` to 1-2
3. Decrease `info_threshold` to 200-300

### Problem: Redundant Information
**Solution:** Increase `n_iterations` (forces query refinement)

### Problem: Too Narrow Answers
**Solution:** Increase `max_results` to get diverse sources

### Problem: Information Not Comprehensive
**Solution:** Increase `info_threshold` to require more data

---

## Best Practices

1. **Start with defaults** - 3 iterations, 3 results, 500 threshold
2. **Adjust one parameter at a time** - See individual impact
3. **Test with similar queries** - Validate your settings
4. **Document what works** - Note good configurations for common query types
5. **Balance is key** - Don't maximize all parameters
6. **User's time is valuable** - Respect it with reasonable timeouts

---

## Related Documentation

- See [UI_ENHANCEMENTS.md](UI_ENHANCEMENTS.md) for UI components overview
- See [WEB_SEARCH_THINKING_GUIDE.md](WEB_SEARCH_THINKING_GUIDE.md) for search mechanism
- See [TOOL_CALLING_GUIDE.md](TOOL_CALLING_GUIDE.md) for other available features
