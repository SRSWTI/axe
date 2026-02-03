# Common Use Cases & Workflows

## Common Use Cases

axe can help you complete various software development and general tasks. Here are some typical scenarios.

### Implementing new features

When you need to add new features to your project, simply describe your requirements in natural language. axe will automatically read relevant code, understand the project structure, and then make modifications.

```
Add pagination to the user list page, showing 20 records per page
```

axe typically works through a "Read → Edit → Verify" workflow:
1. **Read**: Search and read relevant code, understand existing implementation
2. **Edit**: Write or modify code, following the project's coding style
3. **Verify**: Run tests or builds to ensure changes don't introduce issues

If you're not satisfied with the changes, you can tell axe to adjust:

```
The pagination component style doesn't match the rest of the project, reference the Button component's style
```

### Fixing bugs

Describe the problem you're encountering, and axe will help you locate the cause and fix it:

```
After user login, when redirecting to the home page, it occasionally shows logged out status. Help me investigate
```

For problems with clear error messages, you can paste the error log directly:

```
When running npm test, I get this error:

TypeError: Cannot read property 'map' of undefined
    at UserList.render (src/components/UserList.jsx:15:23)

Please fix it
```

You can also have axe run commands to reproduce and verify the issue:

```
Run the tests, and if there are any failing cases, fix them
```

### Understanding projects

axe can help you explore and understand unfamiliar codebases:

```
What's the overall architecture of this project? Where is the entry file?
```

```
How is the user authentication flow implemented? What files are involved?
```

```
Explain what the src/core/scheduler.py file does
```

If you encounter parts you don't understand while reading code, you can ask anytime:

```
What's the difference between useCallback and useMemo? Why use useCallback here?
```

### Automating small tasks

axe can perform various repetitive small tasks:

```
Change all var declarations to const or let in .js files under the src directory
```

```
Add documentation comments to all public functions without docstrings
```

```
Generate unit tests for this API module
```

```
Update all dependencies in package.json to the latest version, then run tests to make sure there are no issues
```

### Automating general tasks

Beyond code-related tasks, axe can also handle general scenarios.

**Research tasks:**
```
Research Python async web frameworks for me, compare the pros and cons of FastAPI, Starlette, and Sanic
```

**Data analysis:**
```
Analyze the access logs in the logs directory, count the call frequency and average response time for each endpoint
```

**Batch file processing:**
```
Convert all PNG images in the images directory to JPEG format, save to the output directory
```

---

## Workflow examples

### Understanding unfamiliar code
```bash
# See the structure first
/skill:code-structure src/auth/

# Find specific functionality
/skill:code-search "user session management"

# Get function context
/skill:code-context create_session
```

### Safe refactoring
```bash
# Before changing a function, see who calls it
/skill:code-impact validate_token

# Shows:
# - 12 direct callers
# - 3 indirect callers through middleware
# - 8 test files that exercise this function

# Now you know what might break
```

### Debugging
```bash
# Find code related to the error
/skill:code-search "handle database connection errors"

# Read the implementation
ReadFile src/db/connection.py

# Make a fix
StrReplaceFile src/db/connection.py "retry_count = 3" "retry_count = 5"

# Toggle to shell and test
[Ctrl+X]
pytest tests/test_db.py
[Ctrl+X]
```

---

## Visual Demonstrations

### Shell Toggle in Action

Hit **Ctrl+X** to seamlessly switch between axe and your normal shell:

![shell toggle](../assets/axe_gif_axe_sample_toggle_shell.gif)

### Precision vs. Basic Search

See the difference between basic grep-based agents and axe-dig's intelligent code understanding:

![comparison](../assets/axe_gif_comparison.gif)

**Left:** Basic CLI agent with grep  
**Right:** axe with axe-dig tools

The precision advantage is clear—axe understands code structure and dependencies, not just text matching.
