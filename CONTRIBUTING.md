# Contributing to AI Knowledge Server

Thank you for contributing to this knowledge base! This guide will help you add high-quality markdown content that AI agents can effectively use.

## How to Contribute

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/Configuring-locally-hosted-ai-knowledge-servers.git
cd Configuring-locally-hosted-ai-knowledge-servers
```

### 2. Create a Branch

```bash
git checkout -b add-knowledge-topic-name
```

### 3. Add Your Knowledge File

Create a new markdown file in the `knowledge/` directory:

```bash
# Use a descriptive filename
touch knowledge/your-topic-name.md
```

### 4. Follow the Template

Use this structure for your knowledge file:

```markdown
# Topic Name

## Overview
Brief description of the topic

## Key Concepts
Main ideas and terminology

## Implementation
Code examples and technical details

## Best Practices
Recommended approaches

## Common Issues
Troubleshooting tips

## References
Related documentation and links
```

### 5. Commit and Push

```bash
git add knowledge/your-topic-name.md
git commit -m "Add knowledge: your topic name"
git push origin add-knowledge-topic-name
```

### 6. Create a Pull Request

- Go to the repository on GitHub
- Click "New Pull Request"
- Select your branch
- Describe what knowledge you're adding

## Content Guidelines

### Writing Style

✅ **Do:**
- Be clear and concise
- Use active voice
- Include working code examples
- Explain the "why" behind concepts
- Keep content up-to-date

❌ **Don't:**
- Use overly complex language
- Include outdated information
- Copy large amounts of external content without attribution
- Leave code examples incomplete

### Code Examples

Always include complete, working code examples:

```python
# Good - Complete and runnable
def calculate_total(items, tax_rate=0.1):
    """Calculate total with tax."""
    subtotal = sum(items)
    return subtotal * (1 + tax_rate)

# Usage example
items = [10.0, 20.0, 30.0]
total = calculate_total(items)
print(f"Total: ${total:.2f}")
```

### Markdown Formatting

- Use headers hierarchically (# for title, ## for sections, ### for subsections)
- Use code fences with language identifiers (\```python, \```javascript, etc.)
- Use bullet points for lists
- Use tables for structured data
- Add blank lines between sections for readability

### Organization

- One main topic per file
- Break down complex topics into multiple files
- Use subdirectories for related topics
- Link related knowledge files together

## Quality Checklist

Before submitting, ensure your contribution:

- [ ] Has a clear, descriptive filename
- [ ] Follows the recommended structure
- [ ] Includes working code examples
- [ ] Uses proper markdown formatting
- [ ] Contains no spelling or grammar errors
- [ ] Provides value to AI agents and developers
- [ ] Links to related knowledge when relevant

## Review Process

1. **Automated checks**: Basic markdown linting
2. **Peer review**: Community members review for quality
3. **Merge**: Approved contributions are merged

## Getting Help

- Check existing knowledge files in the `knowledge/` directory
- Review examples in the `examples/` directory
- Open an issue if you have questions
- Ask in discussions for guidance

## Code of Conduct

- Be respectful and constructive
- Focus on helpful, accurate content
- Welcome newcomers
- Give credit where credit is due

## License

By contributing, you agree that your contributions will be part of this open knowledge base.

Thank you for helping make this resource better! 🎉
