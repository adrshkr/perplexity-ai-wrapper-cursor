# Research and Labs Mode Support

This document explains how to use Research and Labs mode functionality in the PerplexityWebDriver.

## Overview

The PerplexityWebDriver now supports three different search modes:

- **Search Mode** (default): Standard search for quick answers and general queries
- **Research Mode**: Deep research capabilities for comprehensive analysis and detailed reports
- **Labs Mode**: Experimental features and advanced search capabilities

## Method Signatures

### 1. `select_mode(mode='search', page=None) -> bool`

Select a specific search mode in the Perplexity UI.

**Parameters:**
- `mode` (str): Mode to select - `'search'`, `'research'`, or `'labs'` (default: `'search'`)
- `page` (Page, optional): Page instance to use (default: `self.page`)

**Returns:**
- `bool`: True if mode selected successfully, False otherwise

**Example:**
```python
# Select research mode
success = driver.select_mode('research')

# Select labs mode on a specific page
success = driver.select_mode('labs', page=custom_page)
```

### 2. `search(query, mode='search', wait_for_response=True, timeout=60000, extract_images=False, image_dir=None, structured=False, page=None) -> Union[str, Dict]`

Execute a search query with the specified mode.

**Parameters:**
- `query` (str): Search query string
- `mode` (str): Search mode - `'search'`, `'research'`, or `'labs'` (default: `'search'`)
- `wait_for_response` (bool): Wait for complete response (default: True)
- `timeout` (int): Timeout in milliseconds (default: 60000 = 60 seconds)
- `extract_images` (bool): Extract images from response (default: False)
- `image_dir` (str, optional): Directory to save images
- `structured` (bool): Return structured response (default: False)
- `page` (Page, optional): Page instance to use (default: `self.page`)

**Returns:**
- `str`: Response text (if `structured=False`)
- `Dict`: Structured response with sources and metadata (if `structured=True`)

**Structured Response Format:**
```python
{
    'query': str,
    'answer': str,
    'sources': list,
    'related_questions': list,
    'mode': str,  # The mode used for the search
    'model': str,
    'timestamp': str
}
```

## Usage Examples

### Basic Usage

```python
from src.automation.web_driver import PerplexityWebDriver

# Initialize driver
driver = PerplexityWebDriver(headless=True)
driver.start()
driver.navigate_to_perplexity()

# Standard search
result = driver.search("What is AI?")

# Research mode for comprehensive analysis
result = driver.search("Analyze Tesla's financial performance over the last 5 years", mode='research')

# Labs mode for experimental features
result = driver.search("Generate a report on latest AI breakthroughs", mode='labs')
```

### Advanced Usage with Structured Responses

```python
# Get structured response with sources
response = driver.search(
    "Compare renewable energy technologies and their future potential",
    mode='research',
    structured=True,
    extract_images=True
)

print(f"Query: {response['query']}")
print(f"Mode: {response['mode']}")
print(f"Answer: {response['answer'][:200]}...")
print(f"Sources: {len(response['sources'])}")
print(f"Related questions: {len(response['related_questions'])}")

# Export the response
from pathlib import Path
export_path = driver.export_to_local(
    response_data=response,
    format='markdown',
    custom_filename='renewable_energy_analysis'
)
print(f"Exported to: {export_path}")
```

### Mode Selection and Verification

```python
# Manually select mode before searching
success = driver.select_mode('research')
if success:
    print("Research mode activated")
    
    # Verify current mode
    current_mode = getattr(driver, '_current_mode', 'unknown')
    print(f"Current mode: {current_mode}")
    
    # Perform search
    result = driver.search("Comprehensive analysis of blockchain technology")
else:
    print("Failed to activate research mode")
```

## Mode-Specific Use Cases

### Search Mode (Default)
Use for:
- Quick answers to factual questions
- General knowledge queries
- Simple information retrieval

**Example queries:**
- "What is the capital of France?"
- "How many planets are in our solar system?"
- "Define machine learning"

### Research Mode
Use for:
- Comprehensive analysis and reports
- Multi-faceted topics requiring deep understanding
- Academic or professional research
- Market analysis and trends

**Example queries:**
- "Analyze the impact of climate change on global agriculture"
- "Compare different investment strategies for long-term wealth building"
- "Research the latest developments in quantum computing"

### Labs Mode
Use for:
- Experimental features and cutting-edge capabilities
- Creative content generation
- Advanced analytical tasks
- Future-focused technology exploration

**Example queries:**
- "Generate a futuristic scenario for smart cities in 2050"
- "Create an innovative marketing strategy using AI"
- "Design a comprehensive plan for sustainable living"

## Implementation Details

### Mode Button Selectors

The implementation uses robust selectors to identify and click mode buttons:

```javascript
// The implementation automatically detects and clicks:
button[aria-label="Search"]    // For search mode
button[aria-label="Research"]  // For research mode  
button[aria-label="Labs"]      // For labs mode
```

### Error Handling

The implementation includes comprehensive error handling:

- **Disabled Modes**: If a mode is not available for your account, the system logs a warning and continues
- **Already Selected**: If the requested mode is already active, no redundant clicking occurs
- **Network Issues**: Robust retry logic handles temporary connectivity problems
- **UI Changes**: The implementation is designed to be resilient to minor UI changes

### Performance Considerations

- Mode selection adds minimal overhead (< 1 second)
- Research and Labs modes may take longer to generate responses due to their comprehensive nature
- Consider using longer timeouts for complex research queries

## Troubleshooting

### Common Issues

1. **Mode buttons not found**
   - Ensure you're logged into Perplexity
   - Check that your account has access to the requested mode
   - Verify the page has fully loaded

2. **Mode selection fails**
   - Some modes may be disabled for certain account types
   - Check the logs for specific error messages
   - Try selecting a different mode

3. **Research/Labs mode not available**
   - These modes may require specific account permissions
   - Some features might be in beta or limited availability
   - Contact Perplexity support for account-specific issues

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show detailed logs about mode selection
driver.select_mode('research')
```

## Best Practices

1. **Use appropriate modes**: Match the mode to your query complexity
2. **Handle timeouts**: Research and Labs modes may need longer timeouts
3. **Check structured responses**: Use `structured=True` for programmatic processing
4. **Export results**: Use the export functionality for persistent storage
5. **Monitor logs**: Check logs for mode selection success/failure

## Migration Guide

If you're updating existing code:

**Before:**
```python
result = driver.search("Your query")
```

**After (with mode support):**
```python
# Default behavior unchanged
result = driver.search("Your query")  # Still uses search mode

# New: Use research mode
result = driver.search("Your query", mode='research')

# New: Use labs mode
result = driver.search("Your query", mode='labs')

# New: Get structured response
result = driver.search("Your query", mode='research', structured=True)
```

The existing API remains fully backward compatible.
