# Knowledge Base

This directory contains markdown files that serve as context for AI agents in GitHub Codespaces.

## How to Add Knowledge Files

1. Create a new `.md` file in this directory
2. Use descriptive filenames (e.g., `api-authentication.md`, `database-schema.md`)
3. Follow markdown best practices for formatting
4. Include code examples where relevant
5. Keep content organized with clear headers

## File Organization Tips

### By Topic
```
knowledge/
├── api/
│   ├── authentication.md
│   ├── endpoints.md
│   └── rate-limiting.md
├── database/
│   ├── schema.md
│   └── migrations.md
└── deployment/
    ├── docker.md
    └── kubernetes.md
```

### By Feature
```
knowledge/
├── user-management.md
├── payment-processing.md
├── notification-system.md
└── reporting-module.md
```

## Example Content Structure

Each knowledge file should include:

```markdown
# Feature/Topic Name

## Overview
Brief description of what this covers

## Key Concepts
Important concepts and terminology

## Implementation Details
Code examples and technical details

## Common Patterns
Reusable patterns and best practices

## Troubleshooting
Common issues and solutions

## Related Documentation
Links to other relevant knowledge files
```

## Getting Started

If this is your first time adding knowledge:

1. Check the `/examples` directory for templates
2. Copy an example template to this directory
3. Customize it with your specific knowledge
4. Commit and push your changes

## Best Practices

- **Be Specific**: Include concrete examples
- **Stay Current**: Update as systems evolve
- **Link Related Content**: Reference other knowledge files
- **Use Code Blocks**: Include working code examples
- **Add Context**: Explain the "why" behind decisions
